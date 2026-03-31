"""AI chat endpoint with role-aware context and tool calling."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import AuthIdentity, InstructorIdentity, StudentIdentity, require_any_auth, validate_student_topology
from database import get_db
from models import Topology
from services import llm_service, llm_tools

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])

# ── System prompts ─────────────────────────────────────────────────

STUDENT_SYSTEM_PROMPT = """You are an AI teaching assistant for AE3GIS, a network topology and security lab platform. You help students with a deployed network topology.

Your role:
- Help understand networking concepts (routing, subnetting, VLANs, firewalls, NAT, DNS)
- Troubleshoot connectivity issues in their topology
- Explain ICS/SCADA security concepts when relevant (PLCs, HMIs, Modbus, OT networks)
- Guide through security exercises without giving away answers directly

CRITICAL RULES:
1. Use the tool_calls mechanism to call tools. NEVER write tool calls as JSON text.
2. Use ONLY the exact container names from the "Available Containers" list below.
3. Do NOT repeat or list the topology information — you already have it in context.
4. Only call tools that are necessary to answer the user's question. Do NOT call get_topology_summary or get_container_details unless the user specifically asks for that information.
5. Keep responses SHORT and focused. Answer the question, explain briefly, done.
6. You can only run read-only diagnostics — tell students to use the terminal for changes."""

INSTRUCTOR_SYSTEM_PROMPT = """You are an AI assistant for AE3GIS, a network topology and security lab platform. You help instructors manage topologies and student lab environments.

Your capabilities:
- Run any command on deployed containers (configure routes, firewalls, interfaces, services)
- Analyze network paths and connectivity
- Generate descriptions of topologies for documentation
- Generate entirely new topologies from natural language descriptions
- Modify existing topologies based on instructions

CRITICAL RULES:
1. Use the tool_calls mechanism to call tools. NEVER write tool calls as JSON text.
2. Use ONLY the exact container names from the "Available Containers" list below.
3. Do NOT repeat or list the topology information — you already have it in context.
4. Only call tools that are necessary. If the user asks you to run a command, just call run_command — do NOT also call get_topology_summary or get_container_details unless needed.
5. Keep responses SHORT. Execute the action, report the result, done.
6. For destructive operations, confirm before executing.

TOPOLOGY GENERATION/MODIFICATION WORKFLOW:
1. When the user asks to create or modify a topology, call generate_topology or modify_topology.
2. Present the summary preview to the user and ask for confirmation.
3. ONLY after the user confirms, call save_topology with the pending_id.
4. Never call save_topology without explicit user confirmation."""

# ── Request/Response models ────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    topology_id: str | None = None
    messages: list[ChatMessage]


class TopologyAction(BaseModel):
    action: str  # "created" or "modified"
    topology_id: str
    name: str


class ChatResponse(BaseModel):
    reply: str
    tool_results: list[dict[str, Any]] | None = None
    topology_action: TopologyAction | None = None


# ── Helpers ────────────────────────────────────────────────────────

# Regex to detect tool calls embedded as text (common with smaller models)
_TOOL_CALL_RE = re.compile(
    r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(\{[^}]+\})\s*\}',
    re.DOTALL,
)


def _extract_text_tool_calls(content: str) -> list[tuple[str, dict]]:
    """Try to extract tool calls that the model wrote as text instead of using tool_calls."""
    results = []
    for match in _TOOL_CALL_RE.finditer(content):
        try:
            name = match.group(1)
            args = json.loads(match.group(2))
            if name in llm_tools.EXECUTORS:
                results.append((name, args))
        except (json.JSONDecodeError, IndexError):
            continue
    return results


def _build_container_list(topo_data: dict) -> str:
    """Build a clear list of container names and IDs for the system prompt."""
    lines = []
    for site in topo_data.get("sites", []):
        for subnet in site.get("subnets", []):
            for c in subnet.get("containers", []):
                lines.append(f'  - "{c["name"]}" (id: {c["id"]}, type: {c["type"]}, ip: {c["ip"]}) in {site["name"]}/{subnet["name"]}')
    return "\n".join(lines) if lines else "  (no containers)"


# ── Endpoint ───────────────────────────────────────────────────────

MAX_TOOL_ROUNDS = 5  # Prevent infinite tool-calling loops


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    identity: AuthIdentity = Depends(require_any_auth),
    db: Session = Depends(get_db),
):
    is_instructor = isinstance(identity, InstructorIdentity)

    # Load topology if provided
    topo = None
    topo_data: dict = {}
    topo_id: str = ""
    if req.topology_id:
        validate_student_topology(identity, req.topology_id)
        topo = db.query(Topology).filter(Topology.id == req.topology_id).first()
        if not topo:
            raise HTTPException(404, "Topology not found")
        topo_data = topo.data if isinstance(topo.data, dict) else {}
        topo_id = topo.id

    # Build system prompt with topology context
    system_prompt = INSTRUCTOR_SYSTEM_PROMPT if is_instructor else STUDENT_SYSTEM_PROMPT
    if topo:
        system_prompt += f"\n\n## Current Topology\n"
        system_prompt += f"Name: {topo.name} | Status: {topo.status}\n"
        container_list = _build_container_list(topo_data)
        system_prompt += f"\n## Containers (use these names in tool calls)\n{container_list}"
    else:
        system_prompt += "\n\n## No topology loaded\nThe user has no topology open. You can help them generate a new one with the generate_topology tool."

    # Select tools based on role
    tools = llm_tools.INSTRUCTOR_TOOLS if is_instructor else llm_tools.STUDENT_TOOLS

    # Build messages
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for msg in req.messages:
        messages.append({"role": msg.role, "content": msg.content})

    # Tool-calling loop
    all_tool_results = []
    topology_action: TopologyAction | None = None

    def _check_topology_action(result: str) -> None:
        """Detect TOPOLOGY_CREATED / TOPOLOGY_MODIFIED markers from save_topology."""
        nonlocal topology_action
        if result.startswith("TOPOLOGY_CREATED:"):
            parts = result.split(":", 2)
            if len(parts) == 3:
                topology_action = TopologyAction(action="created", topology_id=parts[1], name=parts[2])
        elif result.startswith("TOPOLOGY_MODIFIED:"):
            parts = result.split(":", 2)
            if len(parts) == 3:
                topology_action = TopologyAction(action="modified", topology_id=parts[1], name=parts[2])

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = await llm_service.chat_completion(messages, tools=tools)
        except Exception as e:
            log.error("LLM request failed: %s", e)
            raise HTTPException(502, f"LLM service unavailable: {e}")

        assistant_msg = llm_service.extract_reply(response)

        # Check for proper tool calls
        if llm_service.has_tool_calls(assistant_msg):
            messages.append(assistant_msg)

            for tool_call in llm_service.get_tool_calls(assistant_msg):
                fn_name = tool_call["function"]["name"]
                args = llm_service.parse_tool_args(tool_call)

                log.info("Tool call: %s(%s)", fn_name, args)

                # Security: students can't use instructor-only tools
                if not is_instructor and fn_name in llm_tools.INSTRUCTOR_ONLY_TOOLS:
                    result = "Permission denied: this tool requires instructor access."
                else:
                    result = await llm_tools.execute_tool(
                        fn_name, args, topo_data, topo_id,
                        is_instructor=is_instructor, db=db,
                    )

                _check_topology_action(result)

                all_tool_results.append({
                    "tool": fn_name,
                    "args": args,
                    "result": result[:2000],
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                })
            continue  # Loop back for model to process tool results

        # No proper tool calls — check if model wrote tool calls as text
        content = assistant_msg.get("content", "")
        text_tool_calls = _extract_text_tool_calls(content)

        if text_tool_calls:
            log.info("Detected %d text-embedded tool calls, executing them", len(text_tool_calls))
            tool_outputs = []
            for fn_name, args in text_tool_calls:
                if not is_instructor and fn_name in llm_tools.INSTRUCTOR_ONLY_TOOLS:
                    result = "Permission denied: this tool requires instructor access."
                else:
                    result = await llm_tools.execute_tool(
                        fn_name, args, topo_data, topo_id,
                        is_instructor=is_instructor, db=db,
                    )

                _check_topology_action(result)

                all_tool_results.append({
                    "tool": fn_name,
                    "args": args,
                    "result": result[:2000],
                })
                tool_outputs.append(f"[{fn_name}]: {result}")

            # Feed results back so model can generate a proper answer
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": "The tool calls have been executed. Here are the results:\n\n"
                + "\n\n".join(tool_outputs)
                + "\n\nPlease provide your response based on these results. Do not repeat the tool calls.",
            })
            continue  # Loop back for final answer

        # Pure text response — return it
        return ChatResponse(
            reply=content,
            tool_results=all_tool_results or None,
            topology_action=topology_action,
        )

    # Exhausted tool rounds — ask the model for a final answer without tools
    try:
        response = await llm_service.chat_completion(messages, tools=None)
        assistant_msg = llm_service.extract_reply(response)
        return ChatResponse(
            reply=assistant_msg.get("content", "I was unable to complete the analysis."),
            tool_results=all_tool_results or None,
            topology_action=topology_action,
        )
    except Exception:
        return ChatResponse(
            reply="I ran into an issue processing your request. Please try again.",
            tool_results=all_tool_results or None,
            topology_action=topology_action,
        )


@router.get("/health")
async def ai_health():
    """Check if the LLM service is reachable."""
    try:
        response = await llm_service.chat_completion(
            [{"role": "user", "content": "ping"}],
            temperature=0.0,
        )
        model = response.get("model", "unknown")
        return {"status": "ok", "model": model}
    except Exception as e:
        return {"status": "error", "error": str(e)}
