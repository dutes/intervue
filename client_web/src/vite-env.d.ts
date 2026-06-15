/// <reference types="vite/client" />

interface ImportMetaEnv {
    /** Base URL for the backend API. Empty string = same-origin. */
    readonly VITE_API_BASE?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
