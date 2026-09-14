import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Dialog, DialogClose, Field, Input } from '@/ui';
import { subnetSchema, type SubnetFormValues } from '../schemas';

export interface AddSubnetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: SubnetFormValues) => void;
  defaultName?: string;
  /** Suggested CIDR (next free /24). */
  defaultCidr?: string;
}

export function AddSubnetDialog({ open, onOpenChange, onSubmit, defaultName = '', defaultCidr = '' }: AddSubnetDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Add subnet"
      description="A gateway router and a switch are created and linked automatically."
      size="sm"
    >
      {open ? <SubnetForm defaultName={defaultName} defaultCidr={defaultCidr} onSubmit={(v) => { onSubmit(v); onOpenChange(false); }} /> : null}
    </Dialog>
  );
}

function SubnetForm({ defaultName, defaultCidr, onSubmit }: { defaultName: string; defaultCidr: string; onSubmit: (v: SubnetFormValues) => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<SubnetFormValues>({
    resolver: zodResolver(subnetSchema),
    defaultValues: { name: defaultName, cidr: defaultCidr },
  });
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <Field label="Name" error={errors.name?.message} required>
        {(ctl) => <Input {...ctl} {...register('name')} autoFocus placeholder="e.g. Control LAN" />}
      </Field>
      <Field label="CIDR" error={errors.cidr?.message} hint="IPv4 network in CIDR notation." required>
        {(ctl) => <Input {...ctl} {...register('cidr')} mono placeholder="10.0.1.0/24" />}
      </Field>
      <div className="flex justify-end gap-2 pt-1">
        <DialogClose asChild><Button variant="ghost">Cancel</Button></DialogClose>
        <Button type="submit" variant="primary">Add subnet</Button>
      </div>
    </form>
  );
}
