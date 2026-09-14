import { TooltipProvider, Toaster } from '@/ui';
import { useApplyTheme } from './theme';

export function Providers({ children }: { children: React.ReactNode }) {
  const theme = useApplyTheme();
  return (
    <TooltipProvider delayDuration={400} skipDelayDuration={200}>
      {children}
      <Toaster theme={theme} />
    </TooltipProvider>
  );
}
