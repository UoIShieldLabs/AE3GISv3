import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '../store/AuthContext';
import { aiChat, type AiChatMessage, type AiToolResult, type AiTopologyAction } from '../api/client';
import './AiChatPanel.css';

interface AiChatPanelProps {
  open: boolean;
  onClose: () => void;
  topologyId: string | null;
  onTopologyAction?: (action: AiTopologyAction) => void;
}

interface ChatEntry {
  role: 'user' | 'assistant';
  content: string;
  toolResults?: AiToolResult[];
  topologyAction?: AiTopologyAction;
  error?: boolean;
}

export function AiChatPanel({ open, onClose, topologyId, onTopologyAction }: AiChatPanelProps) {
  const auth = useAuth();
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Focus input when panel opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  const toggleToolExpand = useCallback((index: number) => {
    setExpandedTools(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  const handleCancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userEntry: ChatEntry = { role: 'user', content: text };
    setMessages(prev => [...prev, userEntry]);
    setInput('');
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    // Build message history for the API (last 20 messages to limit context)
    const history: AiChatMessage[] = [...messages, userEntry]
      .slice(-20)
      .map(m => ({ role: m.role, content: m.content }));

    try {
      const resp = await aiChat(topologyId, history, controller.signal);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: resp.reply,
          toolResults: resp.tool_results ?? undefined,
          topologyAction: resp.topology_action ?? undefined,
        },
      ]);
      if (resp.topology_action && onTopologyAction) {
        onTopologyAction(resp.topology_action);
      }
    } catch (err) {
      if (controller.signal.aborted) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: 'Request cancelled.', error: true },
        ]);
      } else {
        const errMsg = err instanceof Error ? err.message : 'Failed to get response';
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: errMsg, error: true },
        ]);
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  }, [input, loading, topologyId, messages]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleClear = useCallback(() => {
    setMessages([]);
    setExpandedTools(new Set());
  }, []);

  if (!open) return null;

  return (
    <div className="ai-chat-panel">
      <div className="ai-chat-header">
        <span className="ai-chat-title">
          AI Assistant
          <span className="ai-chat-role">({auth.role})</span>
        </span>
        <div className="ai-chat-header-actions">
          <button className="ai-chat-clear" onClick={handleClear} title="Clear chat">
            Clear
          </button>
          <button className="ai-chat-close" onClick={onClose} title="Close">
            x
          </button>
        </div>
      </div>

      <div className="ai-chat-messages">
        {messages.length === 0 && (
          <div className="ai-chat-empty">
            {auth.role === 'student' && !topologyId ? (
              <p>Save or load a topology first to start chatting.</p>
            ) : auth.role === 'student' ? (
              <>
                <p>Ask me about your network topology:</p>
                <ul>
                  <li>"Why can't my workstation ping the server?"</li>
                  <li>"Explain the routing between subnets"</li>
                  <li>"What is the subnet mask for 10.0.1.0/24?"</li>
                  <li>"Show me the network path from A to B"</li>
                </ul>
              </>
            ) : (
              <>
                <p>I can help you manage your topology:</p>
                <ul>
                  <li>"Create a topology with a corporate LAN and DMZ"</li>
                  <li>"Add a SCADA subnet with 2 PLCs and an HMI"</li>
                  <li>"Describe this network for a lab handout"</li>
                  <li>"Run a ping from workstation-1 to the server"</li>
                </ul>
              </>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`ai-chat-msg ai-chat-msg-${msg.role}${msg.error ? ' ai-chat-msg-error' : ''}`}
          >
            <div className="ai-chat-msg-label">
              {msg.role === 'user' ? 'You' : 'AI'}
            </div>
            <div className="ai-chat-msg-content">
              {msg.content.split('\n').map((line, j) => (
                <span key={j}>
                  {line}
                  {j < msg.content.split('\n').length - 1 && <br />}
                </span>
              ))}
            </div>
            {msg.topologyAction && (
              <div className="ai-chat-topo-action">
                {msg.topologyAction.action === 'created'
                  ? `New topology "${msg.topologyAction.name}" created.`
                  : `Topology "${msg.topologyAction.name}" updated.`}
              </div>
            )}
            {msg.toolResults && msg.toolResults.length > 0 && (
              <div className="ai-chat-tools">
                <button
                  className="ai-chat-tools-toggle"
                  onClick={() => toggleToolExpand(i)}
                >
                  {expandedTools.has(i) ? 'Hide' : 'Show'} tool calls ({msg.toolResults.length})
                </button>
                {expandedTools.has(i) && (
                  <div className="ai-chat-tools-list">
                    {msg.toolResults.map((tr, k) => (
                      <div key={k} className="ai-chat-tool-result">
                        <div className="ai-chat-tool-name">
                          {tr.tool}({Object.entries(tr.args).map(([key, val]) => `${key}="${val}"`).join(', ')})
                        </div>
                        <pre className="ai-chat-tool-output">{tr.result}</pre>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="ai-chat-msg ai-chat-msg-assistant">
            <div className="ai-chat-msg-label">AI</div>
            <div className="ai-chat-msg-content ai-chat-typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="ai-chat-input-area">
        <textarea
          ref={inputRef}
          className="ai-chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            auth.role === 'student' && !topologyId
              ? 'Load a topology first...'
              : loading
                ? 'Waiting for response...'
                : topologyId
                  ? 'Ask about your network...'
                  : 'Describe a topology to generate...'
          }
          disabled={(auth.role === 'student' && !topologyId) || loading}
          rows={1}
        />
        {loading ? (
          <button
            className="ai-chat-cancel"
            onClick={handleCancel}
          >
            Cancel
          </button>
        ) : (
          <button
            className="ai-chat-send"
            onClick={handleSend}
            disabled={!input.trim() || (auth.role === 'student' && !topologyId)}
          >
            Send
          </button>
        )}
      </div>
    </div>
  );
}
