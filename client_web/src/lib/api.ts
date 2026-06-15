// Base URL for the backend API.
//
// Empty string => same-origin requests, which is what we want in production where FastAPI
// serves the built frontend and the API together. In local dev the Vite server runs on a
// different port, so .env.development points this at the local backend.
export const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function apiUrl(path: string): string {
    return `${API_BASE}${path}`;
}
