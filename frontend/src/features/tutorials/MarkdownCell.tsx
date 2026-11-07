import { useAppStore } from '@/store';
import type { TutorialMarkdownCell } from '@/types/topology';
import { CommitTextarea } from './CommitTextarea';
import { Markdown } from './Markdown';

export interface MarkdownCellProps {
  tutorialId: string;
  cell: TutorialMarkdownCell;
  editing: boolean;
  /** This note's editor is open (edit mode, one at a time). */
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  tools?: React.ReactNode;
}

/** A note: rendered Markdown; in edit mode, click it to write. */
export function MarkdownCell({ tutorialId, cell, editing, open, onOpen, onClose, tools }: MarkdownCellProps) {
  const hasText = !!cell.source.trim();
  if (!editing) return hasText ? <div data-cell-id={cell.id} className="px-0.5"><Markdown source={cell.source} /></div> : null;

  if (open) {
    return (
      <div data-cell-id={cell.id}>
        <CommitTextarea
          autoFocus
          className="font-mono text-xs leading-relaxed"
          value={cell.source}
          onCommit={(source) => useAppStore.getState().updateTutorialCell(tutorialId, cell.id, { source })}
          onBlur={onClose}
          placeholder={'Notes in Markdown — **bold**, `code`, - lists, ## headings'}
          aria-label="Note"
        />
        <p className="mt-1 text-2xs text-fg-subtle">Markdown · click outside to finish · Esc to discard</p>
      </div>
    );
  }

  return (
    <div
      data-cell-id={cell.id}
      role="button"
      tabIndex={0}
      aria-label="Edit note"
      onClick={onOpen}
      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); onOpen(); } }}
      className="group/cell relative cursor-text rounded-md border border-dashed border-transparent px-2 py-1.5 transition-colors hover:border-border-strong focus-visible:border-accent focus-visible:outline-none"
    >
      {hasText ? <Markdown source={cell.source} /> : <p className="text-xs italic text-fg-subtle">Empty note — click to write</p>}
      {tools ? (
        <div
          className="absolute -top-3 right-1 flex rounded-md border border-border bg-surface opacity-0 shadow-sm transition-opacity group-hover/cell:opacity-100 group-focus-within/cell:opacity-100"
          onClick={(e) => e.stopPropagation()}
        >
          {tools}
        </div>
      ) : null}
    </div>
  );
}
