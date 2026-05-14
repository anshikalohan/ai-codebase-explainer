// Session
export interface Session {
  session_id: string;
  source: 'zip' | 'github';
  source_name: string;
  stats: {
    total_files: number;
    parsed_files: number;
    ignored_files: number;
    total_lines: number;
    chunk_count: number;
  };
  file_tree: FileTreeNode[];
  indexing_complete: boolean;
  chunks_indexed: number;
  chat_turns: number;
}

// File Tree
export interface FileTreeNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  language?: string;
  lines?: number;
  size?: number;
}

// Chat
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  question_type?: string;
  cached?: boolean;
  timestamp: number;
  isLoading?: boolean;
}

export interface Source {
  file_path: string;
  language: string;
  start_line?: number;
  end_line?: number;
  relevance: number;
}

// API Responses
export interface IngestResponse {
  session_id: string;
  message: string;
  stats: Session['stats'];
  file_tree: FileTreeNode[];
  source_name: string;
}

export interface ChatResponse {
  answer: string;
  cached: boolean;
  sources: Source[];
  question_type: string;
}

export interface FileExplainResponse {
  explanation: string;
  cached: boolean;
  file_path: string;
  language?: string;
  lines?: number;
}

export interface FileContentResponse {
  path: string;
  content: string;
  language: string;
  lines: number;
  size_bytes: number;
}

export interface SamplePrompt {
  category: string;
  type: string;
  question: string;
}

// Question types
export type QuestionType = 'general' | 'explain' | 'flow' | 'issues' | 'architecture';

export const QUESTION_TYPES: Record<QuestionType, { label: string; emoji: string; description: string }> = {
  general: { label: 'General', emoji: '💬', description: 'Ask any question' },
  explain: { label: 'Explain', emoji: '📖', description: 'Get detailed explanation' },
  flow: { label: 'Flow', emoji: '🔄', description: 'Trace execution flow' },
  issues: { label: 'Issues', emoji: '🐛', description: 'Find bugs & improvements' },
  architecture: { label: 'Architecture', emoji: '🏗️', description: 'Understand structure' },
};

// Language colors (GitHub-style)
export const LANGUAGE_COLORS: Record<string, string> = {
  python: '#3572A5',
  javascript: '#f1e05a',
  typescript: '#2b7489',
  java: '#b07219',
  go: '#00ADD8',
  rust: '#dea584',
  ruby: '#701516',
  cpp: '#f34b7d',
  c: '#555555',
  csharp: '#178600',
  php: '#4F5D95',
  swift: '#ffac45',
  kotlin: '#F18E33',
  scala: '#c22d40',
  html: '#e34c26',
  css: '#563d7c',
  scss: '#c6538c',
  vue: '#2c3e50',
  markdown: '#083fa1',
  json: '#292929',
  yaml: '#cb171e',
  sql: '#e38c00',
  bash: '#89e051',
  dockerfile: '#384d54',
  terraform: '#623CE4',
  default: '#8b949e',
};
