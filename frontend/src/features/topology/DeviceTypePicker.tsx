import { useMemo } from 'react';
import { Combobox, type ComboboxOption } from '@/ui';
import { colorFor, displayNameFor, categoryLabel } from '@/catalog/catalog';
import { NodeGlyph } from '@/catalog/icons';
import { useAppStore } from '@/store';

export interface DeviceTypePickerProps {
  value: string | undefined;
  onValueChange: (type: string) => void;
  id?: string;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
}

/** Searchable, category-grouped catalog picker. */
export function DeviceTypePicker({ value, onValueChange, ...rest }: DeviceTypePickerProps) {
  const catalog = useAppStore((s) => s.catalog);
  const options = useMemo<ComboboxOption[]>(() => {
    if (!catalog) return [];
    return Object.entries(catalog.types).map(([type, spec]) => ({
      value: type,
      label: spec.displayName || displayNameFor(type),
      group: categoryLabel(spec.category ?? ''),
      keywords: [type, spec.category, spec.label, spec.role].filter(Boolean) as string[],
      description: spec.defaultImage,
      icon: <NodeGlyph type={type} size={16} color={colorFor(type)} />,
    }));
  }, [catalog]);
  return <Combobox value={value} onValueChange={onValueChange} options={options} placeholder="Choose a type…" searchPlaceholder="Search types…" {...rest} />;
}
