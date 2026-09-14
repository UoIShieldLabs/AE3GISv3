/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Optional bearer token, only needed when the backend sets AE3GIS_INSTRUCTOR_TOKEN. */
  readonly VITE_INSTRUCTOR_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
