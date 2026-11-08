import { useEffect } from 'react';
import { RouterProvider } from 'react-router';
import { useAppStore } from '@/store';
import { router } from './router';
import { Providers } from './providers';

export function App() {
  const loadCatalog = useAppStore((s) => s.loadCatalog);

  // The node catalog drives every device colour, label and icon. Fetch it once
  // at start-up; it fails open, so the editor still works when it is missing.
  useEffect(() => { void loadCatalog(); }, [loadCatalog]);

  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}
