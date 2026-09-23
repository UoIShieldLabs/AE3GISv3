import { useMemo, useState } from 'react';
import { Pencil } from 'lucide-react';
import { defaultImageFor, imageNameFor, imageSpecFor, variantsFor } from '@/catalog/catalog';
import { useAppStore } from '@/store';
import { Combobox, Input, type ComboboxOption } from '@/ui';
import { ImageStatusDot } from './ImageStatusBadge';
import { statusLabel } from './status';

const CUSTOM = '__custom__';

export interface ImagePickerProps {
  type: string;
  /** The container's own image; undefined/empty = follow the type's default. */
  value: string | undefined;
  onChange: (image: string | undefined) => void;
  id?: string;
}

/** Pick one of a type's variants (with build status), or type any image ref. */
export function ImagePicker({ type, value, onChange, id }: ImagePickerProps) {
  const images = useAppStore((s) => s.images);
  const catalog = useAppStore((s) => s.catalog);
  const def = defaultImageFor(type);
  const current = value?.trim() || def;
  const variants = useMemo(() => {
    void catalog; // recompute when the catalog loads
    return variantsFor(type).filter((ref) => imageSpecFor(ref)?.stability !== 'hidden' || ref === current);
  }, [catalog, type, current]);
  const isCustom = !variants.includes(current);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(current);
  const [prev, setPrev] = useState(current);
  if (prev !== current) {
    setPrev(current);
    setDraft(current);
  }

  const options = useMemo<ComboboxOption[]>(() => {
    const status = (ref: string) => images?.images.find((i) => i.ref === ref);
    const opts: ComboboxOption[] = variants.map((ref) => {
      const st = status(ref);
      const spec = imageSpecFor(ref);
      const tags = [ref === def ? 'default' : null, spec?.stability === 'experimental' ? 'experimental' : null, st ? statusLabel(st).toLowerCase() : null].filter(Boolean);
      return {
        value: ref,
        label: imageNameFor(ref),
        description: `${ref}${tags.length ? ` · ${tags.join(' · ')}` : ''}`,
        keywords: [ref, spec?.description ?? ''],
        icon: <ImageStatusDot image={st} className="size-2" />,
      };
    });
    opts.push({ value: CUSTOM, label: 'Custom image…', description: 'Any image ref from a registry or this host', icon: <Pencil className="size-3.5" /> });
    return opts;
  }, [variants, images, def]);

  const commit = (ref: string) => onChange(ref && ref !== def ? ref : undefined);

  return (
    <div className="flex flex-col gap-1.5">
      <Combobox
        id={id}
        value={isCustom || editing ? CUSTOM : current}
        onValueChange={(v) => {
          if (v === CUSTOM) { setEditing(true); return; }
          setEditing(false);
          commit(v);
        }}
        options={options}
        searchPlaceholder="Search images…"
        renderValue={(o) => (o.value === CUSTOM ? <span className="truncate font-mono text-xs">{isCustom ? current : 'Custom image…'}</span> : <>{o.icon}<span className="truncate">{o.label}</span></>)}
      />
      {isCustom || editing ? (
        <Input
          value={draft}
          mono
          autoFocus={editing}
          placeholder={def}
          aria-label="Custom image"
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => { commit(draft.trim()); setEditing(false); }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); (e.target as HTMLInputElement).blur(); }
            if (e.key === 'Escape') { setDraft(current); setEditing(false); }
          }}
        />
      ) : null}
    </div>
  );
}
