import { createBrowserRouter, Navigate } from 'react-router';
import { LibraryRoute } from './routes/LibraryRoute';
import { EditorRoute } from './routes/EditorRoute';
import { LoginRoute } from './routes/LoginRoute';
import { DevGallery } from './routes/DevGallery';
import { RequireAuth } from './RequireAuth';

export const router = createBrowserRouter([
  { path: '/login', Component: LoginRoute },
  ...(import.meta.env.DEV ? [{ path: '/_gallery', Component: DevGallery }] : []),
  {
    Component: RequireAuth,
    children: [
      { path: '/', Component: LibraryRoute },
      { path: '/t/:topologyId', Component: EditorRoute },
      { path: '/t/:topologyId/site/:siteId', Component: EditorRoute },
      { path: '/t/:topologyId/site/:siteId/subnet/:subnetId', Component: EditorRoute },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);
