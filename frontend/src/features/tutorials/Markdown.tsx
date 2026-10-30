import { createElement } from 'react';
import ReactMarkdown, { type Components, type ExtraProps } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/cn';

// Raw HTML is never rendered (react-markdown's default), so a tutorial in an
// imported topology can't inject markup or scripts. Styled with theme tokens.

/** A Markdown element with our classes, minus react-markdown's `node` prop. */
function styled(tag: keyof React.JSX.IntrinsicElements, classes: string, extra?: Record<string, string>) {
  return function Styled(props: React.HTMLAttributes<HTMLElement> & ExtraProps) {
    const rest = { ...props };
    delete rest.node;
    return createElement(tag, { ...rest, ...extra, className: cn(classes, props.className) });
  };
}

const Table = styled('table', 'w-full border-collapse text-xs');

const components: Components = {
  h1: styled('h1', 'mb-2 mt-4 text-base font-semibold text-fg first:mt-0'),
  h2: styled('h2', 'mb-1.5 mt-4 text-sm font-semibold text-fg first:mt-0'),
  h3: styled('h3', 'mb-1 mt-3 text-[13px] font-semibold text-fg first:mt-0'),
  h4: styled('h4', 'mb-1 mt-3 text-xs font-semibold uppercase tracking-wide text-fg-muted first:mt-0'),
  p: styled('p', 'my-2 first:mt-0 last:mb-0'),
  ul: styled('ul', 'my-2 list-disc space-y-0.5 pl-5 marker:text-fg-subtle'),
  ol: styled('ol', 'my-2 list-decimal space-y-0.5 pl-5 marker:text-fg-subtle'),
  a: styled('a', 'text-accent underline-offset-2 hover:underline', { target: '_blank', rel: 'noreferrer noopener' }),
  blockquote: styled('blockquote', 'my-2 border-l-2 border-accent/60 pl-3 text-fg-muted'),
  hr: styled('hr', 'my-3 border-border'),
  pre: styled('pre', 'my-2 overflow-x-auto rounded-md border border-border bg-surface-2 px-3 py-2 font-mono text-xs leading-relaxed [&_code]:bg-transparent [&_code]:p-0'),
  code: styled('code', 'rounded bg-surface-2 px-1 py-px font-mono text-[0.92em]'),
  table: (props) => <div className="my-2 overflow-x-auto"><Table {...props} /></div>,
  th: styled('th', 'border border-border bg-surface-2 px-2 py-1 text-left font-semibold'),
  td: styled('td', 'border border-border px-2 py-1 align-top'),
  img: styled('img', 'my-2 max-w-full rounded-md'),
  input: styled('input', 'mr-1.5 align-middle accent-[var(--accent)]'),
};

/** A tutorial note, rendered. */
export function Markdown({ source, className }: { source: string; className?: string }) {
  return (
    <div className={cn('min-w-0 break-words text-[13px] leading-relaxed text-fg', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{source}</ReactMarkdown>
    </div>
  );
}
