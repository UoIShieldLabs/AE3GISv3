import { createBrowserRouter, Navigate } from 'react-router';
import { LibraryRoute } from './routes/LibraryRoute';
import { EditorRoute } from './routes/EditorRoute';
import { DevGallery } from './routes/DevGallery';

export const router = createBrowserRouter([
  { path: '/', Component: LibraryRoute },
  { path: '/t/:topologyId', Component: EditorRoute },
  { path: '/t/:topologyId/site/:siteId', Component: EditorRoute },
  { path: '/t/:topologyId/site/:siteId/subnet/:subnetId', Component: EditorRoute },
  ...(import.meta.env.DEV ? [{ path: '/_gallery', Component: DevGallery }] : []),
  { path: '*', element: <Navigate to="/" replace /> },
]);
