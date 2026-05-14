import { useState } from 'react';
import { Code2, RefreshCw, ChevronRight, Loader2 } from 'lucide-react';
import { FileExplorer } from './FileExplorer';
import { ChatPanel } from './ChatPanel';
import { FileViewer } from './FileViewer';
import type { Session, FileTreeNode } from '../utils/types';

interface Props {
  session: Session;
  isIndexing: boolean;
  onReset: () => void;
}

export function MainWorkspace({ session, isIndexing, onReset }: Props) {
  const [selectedFile, setSelectedFile] = useState<FileTreeNode | null>(null);
  const [viewMode, setViewMode] = useState<'chat' | 'file'>('chat');

  const handleFileSelect = (file: FileTreeNode) => {
    setSelectedFile(file);
    setViewMode('file');
  };

  const handleBackToChat = () => {
    setViewMode('chat');
  };

  return (
    <div className="h-screen flex flex-col bg-terminal-bg">
      {/* Top bar */}
      <header className="border-b border-terminal-border px-4 py-2.5 flex items-center gap-3 shrink-0">
        <div className="flex items-center gap-2">
          <Code2 size={16} className="text-terminal-accent" />
          <span className="font-mono font-semibold text-sm text-terminal-text">CodexAI</span>
        </div>

        <ChevronRight size={12} className="text-terminal-border" />

        <span className="text-terminal-muted text-sm font-mono truncate max-w-[200px]">
          {session.source_name.split('/').pop() || session.source_name}
        </span>

        {isIndexing ? (
          <div className="flex items-center gap-1.5 text-terminal-yellow text-xs ml-2">
            <Loader2 size={11} className="animate-spin" />
            Indexing...
          </div>
        ) : (
          <div className="flex items-center gap-2 ml-2">
            <span className="badge badge-green">
              <span className="w-1.5 h-1.5 rounded-full bg-terminal-green mr-1.5" />
              {session.chunks_indexed} chunks indexed
            </span>
          </div>
        )}

        <div className="ml-auto flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-3 text-xs text-terminal-muted font-mono">
            <span>{session.stats.parsed_files} files</span>
            <span className="text-terminal-border">·</span>
            <span>{session.stats.total_lines?.toLocaleString()} lines</span>
          </div>

          <button
            onClick={onReset}
            className="btn-ghost flex items-center gap-1.5 text-xs"
            title="New session"
          >
            <RefreshCw size={13} />
            <span className="hidden sm:inline">New</span>
          </button>
        </div>
      </header>

      {/* Indexing banner */}
      {isIndexing && (
        <div className="border-b border-terminal-yellow/20 bg-terminal-yellow/5 px-4 py-2 text-xs text-terminal-yellow flex items-center gap-2">
          <Loader2 size={11} className="animate-spin" />
          Building vector index... You can start asking questions once indexing completes.
        </div>
      )}

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Explorer */}
        <aside className="w-64 border-r border-terminal-border shrink-0 flex flex-col hidden md:flex">
          <FileExplorer
            fileTree={session.file_tree}
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            sessionId={session.session_id}
          />
        </aside>

        {/* Content area */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {viewMode === 'file' && selectedFile ? (
            <FileViewer
              sessionId={session.session_id}
              file={selectedFile}
              onBack={handleBackToChat}
            />
          ) : (
            <ChatPanel
              sessionId={session.session_id}
              isIndexing={isIndexing}
              selectedFile={selectedFile}
            />
          )}
        </main>
      </div>
    </div>
  );
}
