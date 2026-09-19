import axios from 'axios';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export function isNetworkOrOfflineError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    return (
      !error.response ||
      error.code === 'ERR_NETWORK' ||
      error.code === 'ECONNABORTED' ||
      error.message.includes('Network Error')
    );
  }
  return false;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as any)?.detail;
    if (typeof detail === 'string' && detail) return detail;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
