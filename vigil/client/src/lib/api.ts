import { Platform } from 'react-native';

import type {
  AnalysisRequest,
  AnalysisResponse,
  ChatResponse,
  HealthResponse,
} from '@/src/types/vigil';

function normalizeBaseUrl(baseUrl: string | undefined) {
  return (baseUrl ?? '').trim().replace(/\/+$/, '');
}

const FALLBACK_API_BASE_URL =
  Platform.OS === 'web' ? 'http://127.0.0.1:8000' : 'http://127.0.0.1:8000';

export const API_BASE_URL =
  normalizeBaseUrl(process.env.EXPO_PUBLIC_API_BASE_URL) || FALLBACK_API_BASE_URL;

function buildUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(path), init);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Ignore JSON parse errors and fall back to the generic message.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export const vigilApi = {
  apiBaseUrl: API_BASE_URL,
  health() {
    return request<HealthResponse>('/health');
  },
  analyse(payload: AnalysisRequest) {
    return request<AnalysisResponse>('/analyse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },
  chat(sessionId: string, message: string) {
    return request<ChatResponse>('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  },
};
