import { Layers, Shapes } from 'lucide-react';
import { useAppStore, type SidebarTab } from '@/store';
import type { Scope } from '@/lib/topology';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui';
import { Palette } from './Palette';
import { Explorer } from './Explorer';

export interface SidebarProps {
  scope: Scope;
  onNavigate: (scope: Scope) => void;
}

export function Sidebar({ scope, onNavigate }: SidebarProps) {
  const tab = useAppStore((s) => s.sidebarTab);
  const setTab = useAppStore((s) => s.setSidebarTab);
  return (
    <aside className="flex h-full min-w-0 flex-col border-r border-border bg-surface">
      <Tabs value={tab} onValueChange={(v) => setTab(v as SidebarTab)} className="flex min-h-0 flex-1 flex-col">
        <TabsList className="px-2">
          <TabsTrigger value="palette"><Shapes /> Palette</TabsTrigger>
          <TabsTrigger value="explorer"><Layers /> Explorer</TabsTrigger>
        </TabsList>
        <TabsContent value="palette" className="min-h-0 flex-1 outline-none data-[state=inactive]:hidden"><Palette scope={scope} /></TabsContent>
        <TabsContent value="explorer" className="min-h-0 flex-1 outline-none data-[state=inactive]:hidden"><Explorer scope={scope} onNavigate={onNavigate} /></TabsContent>
      </Tabs>
    </aside>
  );
}
