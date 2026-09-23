import { useEffect, useMemo, useRef } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Dialog, DialogClose, Field, Input } from '@/ui';
import { displayNameFor } from '@/catalog/catalog';
import { ImagePicker } from '@/features/images/ImagePicker';
import { getNextAvailableIp, getSubnetCapacity } from '@/utils/validation';
import { nextName } from '@/lib/topology';
import type { Subnet } from '@/types/topology';
import { deviceSchema, type DeviceFormValues } from '../schemas';
import { DeviceTypePicker } from '../DeviceTypePicker';

export interface AddDeviceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subnet: Subnet | null;
  onSubmit: (values: DeviceFormValues) => void;
  presetType?: string;
  /** A specific variant picked in the palette (empty: the type's default). */
  presetImage?: string;
}

export function AddDeviceDialog({ open, onOpenChange, subnet, onSubmit, presetType, presetImage }: AddDeviceDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Add device"
      description={subnet ? <>Into <span className="font-medium text-fg">{subnet.name}</span> <span className="font-mono">{subnet.cidr}</span></> : undefined}
      size="md"
    >
      {open && subnet ? <DeviceForm subnet={subnet} presetType={presetType} presetImage={presetImage} onSubmit={(v) => { onSubmit(v); onOpenChange(false); }} /> : null}
    </Dialog>
  );
}

function DeviceForm({ subnet, presetType, presetImage, onSubmit }: { subnet: Subnet; presetType?: string; presetImage?: string; onSubmit: (v: DeviceFormValues) => void }) {
  const takenIps = useMemo(() => subnet.containers.map((c) => c.ip).filter(Boolean), [subnet]);
  const names = useMemo(() => subnet.containers.map((c) => c.name), [subnet]);
  const initialType = presetType ?? 'workstation';
  const schema = useMemo(() => deviceSchema({ cidr: subnet.cidr, takenIps }), [subnet.cidr, takenIps]);

  const { register, handleSubmit, control, watch, setValue, getValues, formState: { errors, dirtyFields } } = useForm<DeviceFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: nextName(names, displayNameFor(initialType)),
      type: initialType,
      image: presetImage ?? '',
      ip: getNextAvailableIp(subnet.cidr, takenIps) ?? '',
    },
  });

  const type = watch('type');
  const image = watch('image');
  // Follow the type with an auto name until the user edits it. The image
  // resets to the new type's default: variants belong to a type.
  const lastType = useRef(type);
  useEffect(() => {
    if (!dirtyFields.name) setValue('name', nextName(names, displayNameFor(type)));
    if (lastType.current !== type) {
      lastType.current = type;
      setValue('image', '');
    }
  }, [type, names, dirtyFields.name, setValue]);
  const capacity = getSubnetCapacity(subnet.cidr);
  const free = Math.max(0, capacity - takenIps.length);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <Field label="Type" error={errors.type?.message} required>
        {(ctl) => (
          <Controller
            control={control}
            name="type"
            render={({ field }) => <DeviceTypePicker id={ctl.id} value={field.value} onValueChange={field.onChange} aria-invalid={ctl['aria-invalid']} />}
          />
        )}
      </Field>
      <Field label="Variant" error={errors.image?.message} hint="The image this device runs.">
        {(ctl) => <ImagePicker id={ctl.id} type={type} value={image} onChange={(v) => setValue('image', v ?? '', { shouldDirty: true })} />}
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Name" error={errors.name?.message} required>
          {(ctl) => <Input {...ctl} {...register('name')} placeholder="e.g. PLC 1" />}
        </Field>
        <Field
          label="IP address"
          error={errors.ip?.message}
          hint={free === 0 ? 'Subnet is full' : `${takenIps.length}/${capacity} used`}
          required
          labelAction={
            <button type="button" className="text-2xs text-accent hover:underline" onClick={() => setValue('ip', getNextAvailableIp(subnet.cidr, takenIps) ?? getValues('ip'))}>
              next free
            </button>
          }
        >
          {(ctl) => <Input {...ctl} {...register('ip')} mono placeholder="10.0.1.10" />}
        </Field>
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <DialogClose asChild><Button variant="ghost">Cancel</Button></DialogClose>
        <Button type="submit" variant="primary">Add device</Button>
      </div>
    </form>
  );
}
