import { LucideProvider } from 'lucide-react';
import { iconStyleFor } from '@/catalog/icons/registry';
import { useAppStore } from '@/store';
import { TooltipProvider, Toaster } from '@/ui';
import { useApplyTheme } from './theme';

export function Providers({ children }: { children: React.ReactNode }) {
  const theme = useApplyTheme();
  // The icon style also sets the weight of every Lucide icon (portals included).
  const strokeWidth = iconStyleFor(useAppStore((s) => s.iconStyle)).uiStrokeWidth;
  return (
    <LucideProvider strokeWidth={strokeWidth}>
      <TooltipProvider delayDuration={400} skipDelayDuration={200}>
        {children}
        <Toaster theme={theme.scheme} />
      </TooltipProvider>
    </LucideProvider>
  );
}
