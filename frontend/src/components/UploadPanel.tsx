import { useState, useCallback, useRef } from 'react';
import { Upload, Github, Code2, Zap, Brain, Search, ArrowRight, Loader2 } from 'lucide-react';
import { ingestZip, ingestGithub } from '../utils/api';
import type { IngestResponse } from '../utils/types';

interface Props {
  onSuccess: (data: IngestResponse) => void;
}

type Tab = 'zip' | 'github';

const DEMO_REPOS = [
  'tiangolo/fastapi',
  'pallets/flask',
  'django/django',
  'expressjs/express',
  'denoland/deno',
];

export function UploadPanel({ onSuccess }: Props) {
  const [tab, setTab] = useState<Tab>('zip');
  const [repoUrl, setRepoUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleZipUpload = useCallback(async (file: File) => {
    if (!file.name.endsWith('.zip')) {
      setError('Please upload a .zip file');
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      const data = await ingestZip(file);
      onSuccess(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsLoading(false);
    }
  }, [onSuccess]);

  const handleGithubSubmit = useCallback(async () => {
    if (!repoUrl.trim()) {
      setError('Please enter a GitHub repository URL');
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      const data = await ingestGithub(repoUrl.trim());
      onSuccess(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch repository');
    } finally {
      setIsLoading(false);
    }
  }, [repoUrl, onSuccess]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleZipUpload(file);
  }, [handleZipUpload]);

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      {/* Header */}
      <header className="border-b border-white/5 bg-black/20 backdrop-blur-md px-6 py-4 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-terminal-accent/10 border border-terminal-accent/30 flex items-center justify-center animate-float shadow-[0_0_15px_rgba(59,130,246,0.2)]">
            <Code2 size={16} className="text-terminal-accent" />
          </div>
          <span className="font-mono font-semibold text-terminal-text">CodexAI</span>
          <span className="text-terminal-muted text-sm ml-1">/ codebase explainer</span>
          <div className="ml-auto">
            <span className="badge badge-green">
              <span className="w-1.5 h-1.5 rounded-full bg-terminal-green mr-1.5 inline-block animate-pulse-slow" />
              v1.0.0
            </span>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="max-w-2xl w-full mx-auto text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-terminal-border bg-terminal-surface text-terminal-muted text-xs font-mono mb-6">
            <Zap size={11} className="text-terminal-yellow" />
            RAG-powered · Groq Llama3 · ChromaDB · Zero Cost
          </div>

          <h1 className="text-4xl font-semibold text-terminal-text mb-4 tracking-tight">
            Understand any codebase<br />
            <span className="text-terminal-accent">instantly</span>
          </h1>

          <p className="text-terminal-muted text-base leading-relaxed">
            Upload a ZIP or paste a GitHub URL. Ask questions in plain English.
            Get precise, context-aware answers powered by RAG.
          </p>
        </div>

        {/* Upload Card */}
        <div className="card w-full max-w-xl mx-auto p-8 mb-8 relative">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-xl -z-10 blur-xl opacity-50"></div>
          {/* Tabs */}
          <div className="flex gap-1 mb-6 p-1.5 bg-black/40 rounded-lg backdrop-blur-md border border-white/5">
            {(['zip', 'github'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); setError(''); }}
                className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all duration-150 flex items-center justify-center gap-2 ${
                  tab === t
                    ? 'bg-terminal-surface text-terminal-text shadow-sm border border-terminal-border'
                    : 'text-terminal-muted hover:text-terminal-text'
                }`}
              >
                {t === 'zip' ? <Upload size={14} /> : <Github size={14} />}
                {t === 'zip' ? 'Upload ZIP' : 'GitHub URL'}
              </button>
            ))}
          </div>

          {tab === 'zip' ? (
            <div
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300 ${
                dragOver
                  ? 'border-terminal-accent bg-terminal-accent/10 scale-105 shadow-[0_0_30px_rgba(59,130,246,0.15)]'
                  : 'border-white/10 hover:border-terminal-accent/50 hover:bg-white/5'
              }`}
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <Upload size={28} className="mx-auto mb-3 text-terminal-muted" />
              <p className="text-terminal-text font-medium mb-1 text-sm">
                Drop your ZIP file here
              </p>
              <p className="text-terminal-muted text-xs">
                or click to browse · max 50MB
              </p>
              <input
                ref={fileRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleZipUpload(f);
                }}
              />
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/user/repository"
                  className="input-field w-full"
                  onKeyDown={(e) => e.key === 'Enter' && handleGithubSubmit()}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {DEMO_REPOS.map((r) => (
                  <button
                    key={r}
                    onClick={() => setRepoUrl(`https://github.com/${r}`)}
                    className="text-xs px-2.5 py-1 rounded-full border border-terminal-border text-terminal-muted hover:text-terminal-accent hover:border-terminal-accent transition-colors"
                  >
                    {r}
                  </button>
                ))}
              </div>
              <button
                onClick={handleGithubSubmit}
                disabled={isLoading || !repoUrl.trim()}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <><Loader2 size={14} className="animate-spin" /> Fetching...</>
                ) : (
                  <><Github size={14} /> Analyze Repository</>
                )}
              </button>
            </div>
          )}

          {isLoading && tab === 'zip' && (
            <div className="mt-4 flex items-center gap-2 text-terminal-muted text-sm">
              <Loader2 size={14} className="animate-spin text-terminal-accent" />
              Parsing and indexing your codebase...
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-terminal-red text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-3 max-w-xl">
          {[
            { icon: <Brain size={13} />, text: 'RAG-powered answers' },
            { icon: <Search size={13} />, text: 'Semantic code search' },
            { icon: <Zap size={13} />, text: 'Groq Llama3 (free)' },
            { icon: <ArrowRight size={13} />, text: 'Execution flow tracing' },
          ].map(({ icon, text }) => (
            <div key={text} className="flex items-center gap-1.5 text-terminal-muted text-xs">
              <span className="text-terminal-accent">{icon}</span>
              {text}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
