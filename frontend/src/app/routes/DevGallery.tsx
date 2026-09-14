import { useState } from 'react';
import { Bell, Plus, Settings, Trash2 } from 'lucide-react';
import {
  Badge, Button, Checkbox, Combobox, Dialog, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator,
  DropdownMenuTrigger, EmptyState, Field, IconButton, Input, Kbd, Select, Separator, Switch, Tabs, TabsContent, TabsList,
  TabsTrigger, Textarea, Tooltip, toast,
} from '@/ui';
import { ThemeToggle } from '@/shell/ThemeToggle';

/** DEV-only page to eyeball every primitive in both themes. */
export function DevGallery() {
  const [open, setOpen] = useState(false);
  const [sel, setSel] = useState<string | undefined>('b');
  const [combo, setCombo] = useState<string | undefined>();
  const [on, setOn] = useState(true);

  return (
    <div className="h-full overflow-auto bg-app p-8 text-fg">
      <div className="mx-auto flex max-w-4xl flex-col gap-8">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold">UI gallery</h1>
          <ThemeToggle />
        </div>

        <Section title="Buttons">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="primary"><Plus /> Primary</Button>
            <Button>Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger"><Trash2 /> Danger</Button>
            <Button variant="danger-soft">Danger soft</Button>
            <Button variant="link">Link</Button>
            <Button loading>Loading</Button>
            <Button disabled>Disabled</Button>
            <IconButton label="Settings"><Settings /></IconButton>
            <IconButton label="Notify" variant="secondary" size="icon-sm" onClick={() => toast.success('Saved', { description: 'Everything is up to date.' })}><Bell /></IconButton>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <Button size="xs">xs</Button><Button size="sm">sm</Button><Button size="md">md</Button><Button size="lg">lg</Button>
          </div>
        </Section>

        <Section title="Badges & Kbd">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>Neutral</Badge><Badge tone="accent">Accent</Badge><Badge tone="success" dot="pulse">Running</Badge>
            <Badge tone="warning" dot>Deploying</Badge><Badge tone="danger" dot>Error</Badge><Badge tone="info">Info</Badge><Badge tone="outline" mono>10.0.1.0/24</Badge>
            <Kbd>⌘</Kbd><Kbd>S</Kbd>
          </div>
        </Section>

        <Section title="Form fields">
          <div className="grid max-w-xl grid-cols-2 gap-4">
            <Field label="Name" required hint="Shown on the canvas.">{(c) => <Input {...c} placeholder="Core Router" />}</Field>
            <Field label="IP address" error="That IP is already used.">{(c) => <Input {...c} mono defaultValue="10.0.1.1" />}</Field>
            <Field label="Type">{(c) => <Select {...c} value={sel} onValueChange={setSel} options={[{ value: 'a', label: 'Router', group: 'Infrastructure' }, { value: 'b', label: 'Switch', group: 'Infrastructure' }, { value: 'c', label: 'PLC', group: 'ICS' }]} />}</Field>
            <Field label="Image">{(c) => <Combobox {...c} value={combo} onValueChange={setCombo} options={[{ value: 'kathara/base', label: 'kathara/base', group: 'Catalog' }, { value: 'kathara/frr', label: 'kathara/frr', group: 'Catalog', description: 'FRRouting' }, { value: 'httpd:alpine', label: 'httpd:alpine', group: 'Servers' }]} mono />}</Field>
            <Field label="Notes" className="col-span-2">{(c) => <Textarea {...c} placeholder="Optional" />}</Field>
            <Field label="Enabled" inline>{() => <Switch checked={on} onCheckedChange={setOn} />}</Field>
            <Field label="Persist" inline>{() => <Checkbox defaultChecked />}</Field>
          </div>
        </Section>

        <Section title="Overlays">
          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={() => setOpen(true)}>Open dialog</Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild><Button>Dropdown</Button></DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem shortcut="⌘D"><Plus /> Duplicate</DropdownMenuItem>
                <DropdownMenuItem><Settings /> Configure</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="danger"><Trash2 /> Delete</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Tooltip content="A helpful hint" shortcut="F"><Button variant="outline">Hover me</Button></Tooltip>
          </div>
          <Dialog open={open} onOpenChange={setOpen} title="Add device" description="Into Control LAN 10.0.1.0/24" footer={<><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button><Button variant="primary" onClick={() => setOpen(false)}>Add</Button></>}>
            <Field label="Name">{(c) => <Input {...c} autoFocus />}</Field>
          </Dialog>
        </Section>

        <Section title="Tabs">
          <Tabs defaultValue="a">
            <TabsList><TabsTrigger value="a">Palette</TabsTrigger><TabsTrigger value="b">Explorer</TabsTrigger></TabsList>
            <TabsContent value="a" className="p-3 text-xs text-fg-muted">Palette content</TabsContent>
            <TabsContent value="b" className="p-3 text-xs text-fg-muted">Explorer content</TabsContent>
          </Tabs>
          <Tabs defaultValue="a" className="mt-3">
            <TabsList variant="pills"><TabsTrigger value="a">Tree</TabsTrigger><TabsTrigger value="b">Circle</TabsTrigger><TabsTrigger value="c">Grid</TabsTrigger></TabsList>
          </Tabs>
        </Section>

        <Section title="Empty state">
          <EmptyState icon={<Plus />} title="No subnets yet" description="Each subnet gets a router and a switch automatically." action={<Button variant="primary" size="sm">Add subnet</Button>} className="rounded-xl border border-dashed border-border-strong" />
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-surface p-5 shadow-sm">
      <h2 className="mb-4 text-xs font-semibold uppercase tracking-wide text-fg-muted">{title}</h2>
      {children}
      <Separator className="mt-4 opacity-0" />
    </section>
  );
}
