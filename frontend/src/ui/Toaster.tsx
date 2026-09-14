import { Toaster as Sonner, toast } from 'sonner';

export { toast };

/** App-wide toast host; theme follows the resolved app theme. */
export function Toaster({ theme }: { theme: 'light' | 'dark' }) {
  return (
    <Sonner
      theme={theme}
      position="bottom-center"
      closeButton
      offset={28}
      toastOptions={{
        classNames: {
          toast:
            '!rounded-lg !border !border-border !bg-elevated !text-fg !shadow-lg !text-[13px] !font-sans',
          description: '!text-fg-muted !text-xs',
          actionButton: '!bg-accent !text-accent-fg',
          cancelButton: '!bg-surface-2 !text-fg',
          closeButton: '!bg-elevated !border-border !text-fg-muted',
        },
      }}
    />
  );
}
