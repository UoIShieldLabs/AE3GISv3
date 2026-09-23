import { useMemo } from 'react';
import { Combobox, type ComboboxOption } from '@/ui';
import { colorFor } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { useCatalogTree } from '@/catalog/useCatalogTree';

export interface DeviceTypePickerProps {
  value: string | undefined;
  onValueChange: (type: string) => void;
  id?: string;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
}

/** Searchable, category-grouped catalog picker. */
export function DeviceTypePicker({ value, onValueChange, ...rest }: DeviceTypePickerProps) {
  const tree = useCatalogTree();
  const options = useMemo<ComboboxOption[]>(
    () =>
      tree.flatMap((cat) =>
        cat.types.map(({ type, spec, name, variants }) => ({
          value: type,
          label: name,
          group: cat.label,
          keywords: [type, spec.category, spec.label, spec.role, ...variants.map((v) => v.name)].filter(Boolean) as string[],
          description: variants.length > 1 ? `${variants.map((v) => v.name).join(' · ')}` : variants[0]?.name,
          icon: <NodeGlyph type={type} size={16} color={colorFor(type)} />,
        })),
      ),
    [tree],
  );
  return <Combobox value={value} onValueChange={onValueChange} options={options} placeholder="Choose a type…" searchPlaceholder="Search types…" {...rest} />;
}
