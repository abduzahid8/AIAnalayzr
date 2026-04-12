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

const DEV_API_BASE_URL =
  Platform.OS === 'web' ? 'http://127.0.0.1:8000' : 'http://127.0.0.1:8000';

const configuredUrl = normalizeBaseUrl(process.env.EXPO_PUBLIC_API_BASE_URL);

export const API_BASE_URL = configuredUrl || DEV_API_BASE_URL;

export const isProductionApi = Boolean(configuredUrl) && !configuredUrl.includes('127.0.0.1') && !configuredUrl.includes('localhost');

if (!configuredUrl && !__DEV__) {
  console.warn(
    '[vigil] EXPO_PUBLIC_API_BASE_URL is not set — production build will target localhost which will not work on device.',
  );
}

function buildUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

const TIMEOUTS = {
  analyse: 150_000,
  chat: 30_000,
  health: 10_000,
} as const;

async function request<T>(
  path: string,
  init?: RequestInit,
  timeoutMs: number = 30_000,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(buildUrl(path), {
      ...init,
      signal: controller.signal,
    });

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;

      try {
        const payload = (await response.json()) as { detail?: string };
        if (payload.detail) {
          message = payload.detail;
        }
      } catch {
        // fall back to the generic message
      }

      throw new Error(message);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(`Request to ${path} timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export type StreamEvent =
  | { type: 'progress'; stage: string; detail: string; current_stage: number; total_stages: number }
  | { type: 'complete'; data: AnalysisResponse }
  | { type: 'error'; detail: string };

export const vigilApi = {
  apiBaseUrl: API_BASE_URL,
  health() {
    return request<HealthResponse>('/health', undefined, TIMEOUTS.health);
  },
  analyse(payload: AnalysisRequest) {
    return request<AnalysisResponse>(
      '/analyse',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      TIMEOUTS.analyse,
    );
  },
  async analyseStream(
    payload: AnalysisRequest,
    onProgress: (event: StreamEvent) => void,
  ): Promise<AnalysisResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUTS.analyse);

    try {
      const response = await fetch(buildUrl('/analyse/stream'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        let message = `Request failed with status ${response.status}`;
        try {
          const p = (await response.json()) as { detail?: string };
          if (p.detail) message = p.detail;
        } catch { /* use generic */ }
        throw new Error(message);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Streaming not supported');

      const decoder = new TextDecoder();
      let buffer = '';
      let result: AnalysisResponse | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6)) as StreamEvent;
            onProgress(event);
            if (event.type === 'complete') {
              result = event.data;
            }
            if (event.type === 'error') {
              throw new Error(event.detail);
            }
          } catch (e) {
            if (e instanceof Error && e.message !== line.slice(6)) throw e;
          }
        }
      }

      if (!result) throw new Error('Stream ended without a result');
      return result;
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new Error('Analysis stream timed out');
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  },
  chat(sessionId: string, message: string) {
    return request<ChatResponse>(
      '/chat',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
      },
      TIMEOUTS.chat,
    );
  },
};
