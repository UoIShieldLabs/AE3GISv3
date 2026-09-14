import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button, Dialog, DialogClose, Field, Input } from '@/ui';
import { siteSchema, type SiteFormValues } from '../schemas';

export interface AddSiteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: SiteFormValues) => void;
  defaultName?: string;
}

export function AddSiteDialog({ open, onOpenChange, onSubmit, defaultName = '' }: AddSiteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Add site" description="A site groups subnets at one physical location." size="sm">
      {open ? <SiteForm defaultName={defaultName} onSubmit={(v) => { onSubmit(v); onOpenChange(false); }} /> : null}
    </Dialog>
  );
}

function SiteForm({ defaultName, onSubmit }: { defaultName: string; onSubmit: (v: SiteFormValues) => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<SiteFormValues>({
    resolver: zodResolver(siteSchema),
    defaultValues: { name: defaultName, location: '' },
  });
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <Field label="Name" error={errors.name?.message} required>
        {(ctl) => <Input {...ctl} {...register('name')} autoFocus placeholder="e.g. Plant North" />}
      </Field>
      <Field label="Location" error={errors.location?.message}>
        {(ctl) => <Input {...ctl} {...register('location')} placeholder="e.g. Building 2, Rotterdam" />}
      </Field>
      <div className="flex justify-end gap-2 pt-1">
        <DialogClose asChild><Button variant="ghost">Cancel</Button></DialogClose>
        <Button type="submit" variant="primary">Add site</Button>
      </div>
    </form>
  );
}
