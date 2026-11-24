import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/index.css';
import { App } from './app/App';

// A tab left open across a redeploy asks for lazy chunks the new build no
// longer has: load the new build rather than fail. At most once a minute, so a
// chunk that is really missing doesn't reload the tab forever.
window.addEventListener('vite:preloadError', (event) => {
  const key = 'ae3gis.chunkReload';
  try {
    if (Date.now() - Number(sessionStorage.getItem(key) ?? 0) < 60_000) return;
    sessionStorage.setItem(key, String(Date.now()));
  } catch {
    return;
  }
  event.preventDefault();
  window.location.reload();
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
