import { useState, useEffect } from 'react';
import { ArrowLeft, Sparkles, Copy, Check, Loader2, FileCode } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { getFileContent, explainFile } from '../utils/api';
import type { FileTreeNode, FileContentResponse, FileExplainResponse } from '../utils/types';
import { LANGUAGE_COLORS } from '../utils/types';

interface Props {
  sessionId: string;
  file: FileTreeNode;
  onBack: () => void;
}

export function FileViewer({ sessionId, file, onBack }: Props) {
  const [content, setContent] = useState<FileContentResponse | null>(null);
  const [explanation, setExplanation] = useState<FileExplainResponse | null>(null);
  const [loadingContent, setLoadingContent] = useState(true);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'code' | 'explain'>('code');
  const [error, setError] = useState('');

  useEffect(() => {
    setLoadingContent(true);
    setContent(null);
    setExplanation(null);
    setError('');

    getFileContent(sessionId, file.path)
      .then(setContent)
      .catch((err) => setError(err.message))
      .finally(() => setLoadingContent(false));
  }, [sessionId, file.path]);

  const handleExplain = async () => {
    if (explanation) {
      setActiveTab('explain');
      return;
    }
    setLoadingExplanation(true);
    setActiveTab('explain');
    try {
      const result = await explainFile(sessionId, file.path);
      setExplanation(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Explanation failed');
    } finally {
      setLoadingExplanation(false);
    }
  };

  const handleCopy = async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const langColor = LANGUAGE_COLORS[file.language || 'default'] || LANGUAGE_COLORS['default'];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-terminal-border px-4 py-2.5 flex items-center gap-3 shrink-0">
        <button onClick={onBack} className="btn-ghost flex items-center gap-1.5 text-xs">
          <ArrowLeft size={13} />
          Back
        </button>

        <div className="h-4 w-px bg-terminal-border" />

        <div className="flex items-center gap-2 min-w-0">
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: langColor }}
          />
          <FileCode size={13} className="text-terminal-muted shrink-0" />
          <span className="font-mono text-sm text-terminal-text truncate">{file.path}</span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          {content && (
            <span className="text-xs text-terminal-muted font-mono hidden sm:block">
              {content.lines} lines
            </span>
          )}

          <button
            onClick={handleCopy}
            className="btn-ghost flex items-center gap-1.5 text-xs"
            disabled={!content}
          >
            {copied ? (
              <><Check size={12} className="text-terminal-green" /> Copied</>
            ) : (
              <><Copy size={12} /> Copy</>
            )}
          </button>

          <button
            onClick={handleExplain}
            disabled={loadingContent || loadingExplanation}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-terminal-accent/10 border border-terminal-accent/20 text-terminal-accent hover:bg-terminal-accent/20 transition-colors text-xs font-medium"
          >
            {loadingExplanation ? (
              <><Loader2 size={12} className="animate-spin" /> Explaining...</>
            ) : (
              <><Sparkles size={12} /> AI Explain</>
            )}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-terminal-border flex px-4 gap-1 shrink-0">
        {(['code', 'explain'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => tab === 'explain' ? handleExplain() : setActiveTab('code')}
            className={`py-2 px-3 text-xs border-b-2 transition-colors capitalize ${
              activeTab === tab
                ? 'border-terminal-accent text-terminal-accent'
                : 'border-transparent text-terminal-muted hover:text-terminal-text'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {error && (
          <div className="m-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-terminal-red text-sm">
            {error}
          </div>
        )}

        {activeTab === 'code' ? (
          loadingContent ? (
            <div className="flex items-center justify-center h-32 text-terminal-muted text-sm gap-2">
              <Loader2 size={16} className="animate-spin" />
              Loading file...
            </div>
          ) : content ? (
            <pre className="p-4 text-xs font-mono text-terminal-text overflow-auto leading-relaxed">
              <code className={`language-${content.language}`}>
                {content.content}
              </code>
            </pre>
          ) : null
        ) : (
          <div className="p-4">
            {loadingExplanation ? (
              <div className="flex items-center gap-3 text-terminal-muted text-sm py-8 justify-center">
                <Loader2 size={16} className="animate-spin text-terminal-accent" />
                Generating AI explanation...
              </div>
            ) : explanation ? (
              <div className="prose text-terminal-text text-sm max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                >
                  {explanation.explanation}
                </ReactMarkdown>
                {explanation.cached && (
                  <p className="text-[10px] text-terminal-muted mt-4 flex items-center gap-1 font-mono">
                    ⚡ cached response
                  </p>
                )}
              </div>
            ) : (
              <p className="text-terminal-muted text-sm text-center py-8">
                Click "AI Explain" to generate an explanation
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
