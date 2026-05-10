import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send, Sparkles, Zap, RefreshCw, ChevronDown, FileCode, AlertCircle, Copy, Check, Trash2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { streamChatMessage, getSamplePrompts } from '../utils/api';
import type { ChatMessage, SamplePrompt, QuestionType, FileTreeNode } from '../utils/types';
import { QUESTION_TYPES } from '../utils/types';

interface Props {
  sessionId: string;
  isIndexing: boolean;
  selectedFile: FileTreeNode | null;
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1 px-1">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="typing-dot w-1.5 h-1.5 rounded-full bg-terminal-accent"
          />
        ))}
      </div>
    </div>
  );
}

function CodeBlock({ children, className, language }: any) {
  const [copied, setCopied] = useState(false);

  const extractText = (node: any): string => {
    if (typeof node === 'string') return node;
    if (Array.isArray(node)) return node.map(extractText).join('');
    if (node?.props?.children) return extractText(node.props.children);
    return '';
  };

  const handleCopy = () => {
    const text = extractText(children);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!language) {
    return <code className={className}>{children}</code>;
  }

  return (
    <div className="relative group rounded-lg overflow-hidden border border-terminal-border bg-black/40 my-4 shadow-lg animate-fade-in">
      <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-terminal-border text-xs font-mono text-terminal-muted">
        <span className="uppercase tracking-wider">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 hover:text-terminal-text transition-colors py-1"
          title="Copy code"
        >
          {copied ? <Check size={14} className="text-terminal-green" /> : <Copy size={14} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <div className="p-4 overflow-x-auto text-sm font-mono">
        <code className={className}>{children}</code>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-mono font-bold mt-0.5 ${
          isUser
            ? 'bg-terminal-accent/20 text-terminal-accent border border-terminal-accent/30'
            : 'bg-terminal-surface border border-terminal-border text-terminal-muted'
        }`}
      >
        {isUser ? 'U' : <Sparkles size={12} />}
      </div>

      {/* Content */}
      <div className={`flex-1 min-w-0 ${isUser ? 'flex justify-end' : ''}`}>
        {isUser ? (
          <div className="bg-terminal-accent/10 border border-terminal-accent/20 rounded-xl rounded-tr-sm px-4 py-2.5 max-w-lg text-sm text-terminal-text">
            {message.content}
          </div>
        ) : (
          <div className="space-y-3">
            {message.isLoading ? (
              <div className="bg-terminal-surface border border-terminal-border rounded-xl rounded-tl-sm px-4 py-3">
                <TypingIndicator />
              </div>
            ) : (
              <div className="bg-terminal-surface border border-terminal-border rounded-xl rounded-tl-sm px-4 py-3">
                <div className="prose text-terminal-text text-sm max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                    components={{
                      code(props) {
                        const { children, className, node, ...rest } = props;
                        const match = /language-(\w+)/.exec(className || '');
                        return match ? (
                          <CodeBlock language={match[1]} className={className}>
                            {children}
                          </CodeBlock>
                        ) : (
                          <code className="bg-terminal-bg px-1.5 py-0.5 rounded text-terminal-accent font-mono text-[13px]" {...rest}>
                            {children}
                          </code>
                        );
                      }
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>

                {/* Sources */}
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-terminal-border">
                    <p className="text-[10px] uppercase tracking-widest text-terminal-muted mb-2 font-mono">
                      Sources
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {message.sources.slice(0, 5).map((src, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-1.5 px-2 py-1 bg-terminal-bg rounded-md border border-terminal-border text-[11px] font-mono text-terminal-muted"
                          title={src.file_path}
                        >
                          <FileCode size={10} className="text-terminal-accent shrink-0" />
                          <span className="truncate max-w-[140px]">
                            {src.file_path.split('/').pop()}
                          </span>
                          {src.start_line && (
                            <span className="text-terminal-border">:{src.start_line}</span>
                          )}
                          <span className="text-terminal-green ml-1">
                            {Math.round(src.relevance * 100)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="flex items-center gap-3 mt-2">
                  {message.cached && (
                    <span className="text-[10px] text-terminal-muted flex items-center gap-1">
                      <Zap size={9} className="text-terminal-yellow" />
                      cached
                    </span>
                  )}
                  {message.question_type && message.question_type !== 'general' && (
                    <span className="text-[10px] text-terminal-muted">
                      {QUESTION_TYPES[message.question_type as QuestionType]?.emoji}{' '}
                      {QUESTION_TYPES[message.question_type as QuestionType]?.label}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SamplePromptCard({ prompt, onClick }: { prompt: SamplePrompt; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="text-left p-3 card hover:border-terminal-muted transition-colors rounded-xl group"
    >
      <div className="text-[10px] font-mono text-terminal-muted mb-1 uppercase tracking-wider">
        {prompt.category}
      </div>
      <p className="text-xs text-terminal-text group-hover:text-terminal-accent transition-colors line-clamp-2">
        {prompt.question}
      </p>
    </button>
  );
}

export function ChatPanel({ sessionId, isIndexing, selectedFile }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [questionType, setQuestionType] = useState<QuestionType>('general');
  const [isLoading, setIsLoading] = useState(false);
  const [samplePrompts, setSamplePrompts] = useState<SamplePrompt[]>([]);
  const [showTypeMenu, setShowTypeMenu] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    getSamplePrompts()
      .then(setSamplePrompts)
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(
    async (question: string, type: QuestionType = questionType) => {
      if (!question.trim() || isLoading || isIndexing) return;

      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: question,
        timestamp: Date.now(),
      };

      const loadingMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        isLoading: true,
      };

      setMessages((prev) => [...prev, userMessage, loadingMessage]);
      setInput('');
      setIsLoading(true);
      setError('');

      try {
        await streamChatMessage(
          sessionId,
          question,
          type,
          selectedFile?.path,
          (meta) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === loadingMessage.id
                  ? { ...m, isLoading: false, sources: meta.sources, question_type: meta.question_type, cached: meta.cached }
                  : m
              )
            );
          },
          (chunk) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === loadingMessage.id
                  ? { ...m, content: m.content + chunk }
                  : m
              )
            );
          },
          (errMsg) => {
            throw new Error(errMsg);
          }
        );
      } catch (err: unknown) {
        const errorMessage: ChatMessage = {
          id: loadingMessage.id,
          role: 'assistant',
          content: `**Error:** ${err instanceof Error ? err.message : 'Failed to get response. Please try again.'}`,
          timestamp: Date.now(),
        };
        setMessages((prev) =>
          prev.map((m) => (m.id === loadingMessage.id ? errorMessage : m))
        );
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
        inputRef.current?.focus();
      }
    },
    [sessionId, questionType, isLoading, isIndexing, selectedFile]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const currentType = QUESTION_TYPES[questionType];

  return (
    <div className="flex flex-col h-full relative">
      {/* Context & Actions bar */}
      <div className="border-b border-white/5 px-4 py-2 bg-terminal-surface/30 backdrop-blur-md flex items-center justify-between text-xs sticky top-0 z-10">
        <div className="flex items-center gap-2">
          {selectedFile ? (
            <>
              <FileCode size={12} className="text-terminal-accent" />
              <span className="text-terminal-muted">Scoped to:</span>
              <span className="font-mono text-terminal-text">{selectedFile.path}</span>
            </>
          ) : (
            <>
              <Sparkles size={12} className="text-terminal-accent" />
              <span className="text-terminal-muted">Global workspace</span>
            </>
          )}
        </div>
        
        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="flex items-center gap-1.5 text-terminal-muted hover:text-terminal-red transition-colors px-2 py-1 rounded-md hover:bg-white/5"
            title="Clear Chat"
          >
            <Trash2 size={12} />
            <span>Clear Chat</span>
          </button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center py-8 px-4">
            <div className="w-12 h-12 rounded-2xl bg-terminal-surface border border-terminal-border flex items-center justify-center mb-4">
              <Sparkles size={20} className="text-terminal-accent" />
            </div>
            <h2 className="text-terminal-text font-semibold mb-1 text-base">
              {isIndexing ? 'Indexing in progress...' : 'Ready to explore'}
            </h2>
            <p className="text-terminal-muted text-sm text-center mb-8 max-w-sm">
              {isIndexing
                ? 'Vector index is being built. You can start asking questions in a moment.'
                : 'Ask anything about the codebase. Try one of the prompts below to get started.'}
            </p>

            {!isIndexing && samplePrompts.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
                {samplePrompts.slice(0, 4).map((p) => (
                  <SamplePromptCard
                    key={p.question}
                    prompt={p}
                    onClick={() => sendMessage(p.question, p.type as QuestionType)}
                  />
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-terminal-border p-4 shrink-0">
        {error && (
          <div className="mb-3 flex items-center gap-2 text-terminal-red text-xs">
            <AlertCircle size={12} />
            {error}
          </div>
        )}

        <div className="flex gap-2 items-end">
          {/* Question type selector */}
          <div className="relative">
            <button
              onClick={() => setShowTypeMenu((s) => !s)}
              className="h-9 px-2.5 rounded-lg border border-terminal-border bg-terminal-surface hover:border-terminal-muted transition-colors flex items-center gap-1.5 text-xs text-terminal-muted"
              title="Question type"
            >
              <span>{currentType.emoji}</span>
              <ChevronDown size={11} />
            </button>

            {showTypeMenu && (
              <div className="absolute bottom-full left-0 mb-2 w-48 card p-1 shadow-xl z-10 animate-fade-in">
                {Object.entries(QUESTION_TYPES).map(([key, val]) => (
                  <button
                    key={key}
                    onClick={() => {
                      setQuestionType(key as QuestionType);
                      setShowTypeMenu(false);
                    }}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition-colors ${
                      questionType === key
                        ? 'bg-terminal-accent/10 text-terminal-accent'
                        : 'text-terminal-muted hover:bg-terminal-bg hover:text-terminal-text'
                    }`}
                  >
                    <span>{val.emoji}</span>
                    <div className="text-left">
                      <div className="font-medium">{val.label}</div>
                      <div className="text-[10px] opacity-70">{val.description}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isIndexing
                  ? 'Waiting for indexing to complete...'
                  : selectedFile
                  ? `Ask about ${selectedFile.name}...`
                  : 'Ask about the codebase... (Enter to send, Shift+Enter for newline)'
              }
              disabled={isLoading || isIndexing}
              rows={1}
              className="input-field w-full resize-none py-2.5 pr-10 max-h-32 overflow-y-auto disabled:opacity-50"
              style={{ minHeight: '40px' }}
            />
          </div>

          {/* Send button */}
          <button
            onClick={() => sendMessage(input)}
            disabled={isLoading || isIndexing || !input.trim()}
            className="btn-primary h-9 w-9 flex items-center justify-center shrink-0 rounded-lg"
            title="Send (Enter)"
          >
            {isLoading ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
          </button>
        </div>

        <p className="text-[10px] text-terminal-muted mt-2 font-mono">
          {currentType.emoji} {currentType.label} mode
          {selectedFile ? ` · scoped to ${selectedFile.name}` : ' · entire codebase'}
        </p>
      </div>
    </div>
  );
}
