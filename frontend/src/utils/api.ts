import axios, { AxiosError } from 'axios';
import type {
  IngestResponse,
  ChatResponse,
  FileExplainResponse,
  FileContentResponse,
  Session,
  SamplePrompt,
  QuestionType,
} from './types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 120_000,
});

// Request interceptor for logging
api.interceptors.request.use((config) => {
  console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response error normalization
api.interceptors.response.use(
  (res) => res,
  (error: AxiosError<{ detail: string }>) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred';
    throw new Error(message);
  }
);

// ─── Ingest ──────────────────────────────────────────────────────────────

export async function ingestZip(file: File): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post<IngestResponse>('/ingest/zip', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function ingestGithub(repoUrl: string): Promise<IngestResponse> {
  const { data } = await api.post<IngestResponse>('/ingest/github', {
    repo_url: repoUrl,
  });
  return data;
}

// ─── Session ─────────────────────────────────────────────────────────────

export async function getSession(sessionId: string): Promise<Session> {
  const { data } = await api.get<Session>(`/session/${sessionId}`);
  return data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/session/${sessionId}`);
}

// ─── Chat ─────────────────────────────────────────────────────────────────

export async function sendChatMessage(
  sessionId: string,
  question: string,
  questionType: QuestionType = 'general',
  filterFile?: string
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', {
    session_id: sessionId,
    question,
    question_type: questionType,
    filter_file: filterFile,
  });
  return data;
}

export async function streamChatMessage(
  sessionId: string,
  question: string,
  questionType: QuestionType = 'general',
  filterFile?: string,
  onMetadata?: (meta: any) => void,
  onChunk?: (chunk: string) => void,
  onError?: (err: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${BASE_URL}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        question,
        question_type: questionType,
        filter_file: filterFile,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    if (!response.body) throw new Error('ReadableStream not supported.');

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6);
          if (dataStr === '[DONE]') return;
          try {
            const data = JSON.parse(dataStr);
            if (data.type === 'metadata') onMetadata?.(data);
            else if (data.type === 'chunk') onChunk?.(data.text);
            else if (data.type === 'error') onError?.(data.message);
          } catch (e) {}
        }
      }
    }
  } catch (err: any) {
    onError?.(err.message || 'Stream failed');
  }
}

// ─── File ─────────────────────────────────────────────────────────────────

export async function explainFile(
  sessionId: string,
  filePath: string
): Promise<FileExplainResponse> {
  const { data } = await api.post<FileExplainResponse>('/explain/file', {
    session_id: sessionId,
    file_path: filePath,
  });
  return data;
}

export async function getFileContent(
  sessionId: string,
  filePath: string
): Promise<FileContentResponse> {
  const { data } = await api.get<FileContentResponse>(
    `/file/${sessionId}?path=${encodeURIComponent(filePath)}`
  );
  return data;
}

// ─── Utils ────────────────────────────────────────────────────────────────

export async function getSamplePrompts(): Promise<SamplePrompt[]> {
  const { data } = await api.get<{ prompts: SamplePrompt[] }>('/sample-prompts');
  return data.prompts;
}

export async function healthCheck(): Promise<boolean> {
  try {
    await axios.get(`${BASE_URL}/health`);
    return true;
  } catch {
    return false;
  }
}

export default api;
