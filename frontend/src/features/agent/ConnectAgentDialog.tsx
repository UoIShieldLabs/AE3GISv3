import { useEffect, useState } from 'react';
import { Copy, KeyRound, Trash2 } from 'lucide-react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { Button, Dialog, IconButton, Input, Spinner, toast } from '@/ui';
import { ago } from '@/lib/time';

async function copy(text: string, what: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`${what} copied`);
  } catch {
    toast.info(text);
  }
}

function Snippet({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-2xs font-medium uppercase tracking-wide text-fg-subtle">
        {label}
        <IconButton label={`Copy ${label}`} size="icon-xs" onClick={() => void copy(text, label)}>
          <Copy />
        </IconButton>
      </div>
      <pre className="overflow-x-auto whitespace-pre rounded-md border border-border bg-surface-2 px-2.5 py-2 font-mono text-2xs leading-relaxed text-fg">{text}</pre>
    </div>
  );
}

/** Use AE3GIS's tools from an agent outside the app (Claude Code, OpenCode…)
 *  over MCP: the endpoint, a token that acts as you, and ready-to-paste setup. */
export function ConnectAgentDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const accounts = useAppStore((s) => !!s.authRequired);
  const [tokens, setTokens] = useState<api.ApiToken[] | null>(null);
  const [label, setLabel] = useState('');
  const [fresh, setFresh] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const url = `${window.location.origin}/api/v1/mcp`;

  useEffect(() => {
    if (!open || !accounts) return;
    api.listApiTokens().then(setTokens).catch(() => setTokens([]));
  }, [open, accounts]);

  const create = async () => {
    setBusy(true);
    try {
      const made = await api.createApiToken(label.trim() || 'External agent');
      setFresh(made.token);
      setLabel('');
      setTokens(await api.listApiTokens());
    } catch (err) {
      toast.error('Could not make a token', { description: api.errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (id: string) => {
    try {
      await api.revokeApiToken(id);
      setTokens((t) => t?.filter((x) => x.id !== id) ?? null);
    } catch (err) {
      toast.error('Could not revoke the token', { description: api.errorMessage(err) });
    }
  };

  const token = fresh ?? '<your token>';
  const header = accounts ? ` \\\n  --header "Authorization: Bearer ${token}"` : '';
  const claude = `claude mcp add --transport http ae3gis ${url}${header}`;
  const opencode = JSON.stringify(
    { mcp: { ae3gis: { type: 'remote', url, ...(accounts ? { headers: { Authorization: `Bearer ${token}` } } : {}) } } },
    null,
    2,
  );

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) setFresh(null);
        onOpenChange(o);
      }}
      title="Connect an external agent"
      description="Claude Code, Claude Desktop, OpenCode or any MCP client can use the same tools as the in-app agent, as you."
      size="lg"
    >
      <div className="flex flex-col gap-4 text-xs">
        <Snippet label="MCP endpoint (streamable HTTP)" text={url} />
        {accounts ? (
          <section className="flex flex-col gap-2">
            <h3 className="flex items-center gap-1.5 text-[13px] font-medium"><KeyRound className="size-3.5" /> API tokens</h3>
            <p className="text-fg-muted">A token acts as you, with your permissions. It lasts 90 days; changing your password ends it.</p>
            {fresh ? (
              <div className="rounded-md border border-warning/50 bg-warning-soft p-2.5">
                <div className="mb-1 font-medium text-warning">Copy it now: it won’t be shown again.</div>
                <div className="flex items-center gap-2">
                  <code className="min-w-0 flex-1 truncate font-mono text-2xs text-fg">{fresh}</code>
                  <IconButton label="Copy token" size="icon-xs" onClick={() => void copy(fresh, 'Token')}><Copy /></IconButton>
                </div>
              </div>
            ) : null}
            <div className="flex gap-2">
              <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="What it's for, e.g. Claude Code on my laptop" className="flex-1" maxLength={80} />
              <Button size="sm" variant="primary" onClick={() => void create()} loading={busy}>New token</Button>
            </div>
            {tokens === null ? (
              <Spinner />
            ) : tokens.length ? (
              <ul className="divide-y divide-border rounded-md border border-border">
                {tokens.map((t) => (
                  <li key={t.id} className="flex items-center gap-2 px-2.5 py-1.5">
                    <span className="min-w-0 flex-1 truncate">{t.label}</span>
                    <span className="shrink-0 text-2xs text-fg-subtle">made {ago(t.created_at)} · used {ago(t.last_used_at)}</span>
                    <IconButton label="Revoke token" size="icon-xs" variant="ghost" onClick={() => void revoke(t.id)}><Trash2 /></IconButton>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        ) : (
          <p className="text-fg-muted">Accounts are off on this instance, so no token is needed (and anyone who can reach it can use these tools).</p>
        )}
        <Snippet label="Claude Code" text={claude} />
        <Snippet label="OpenCode (opencode.json)" text={opencode} />
      </div>
    </Dialog>
  );
}
