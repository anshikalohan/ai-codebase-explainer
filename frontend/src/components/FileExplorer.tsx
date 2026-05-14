import { useState } from 'react';
import {
  Folder, FolderOpen, FileCode, FileText, ChevronRight, ChevronDown,
} from 'lucide-react';
import { LANGUAGE_COLORS } from '../utils/types';
import type { FileTreeNode } from '../utils/types';

interface Props {
  fileTree: FileTreeNode[];
  selectedFile: FileTreeNode | null;
  onFileSelect: (file: FileTreeNode) => void;
  sessionId: string;
}

function getLanguageColor(lang?: string): string {
  return LANGUAGE_COLORS[lang || 'default'] || LANGUAGE_COLORS['default'];
}

function FileIcon({ language }: { language?: string }) {
  const color = getLanguageColor(language);
  return (
    <span
      className="w-2 h-2 rounded-full shrink-0 mt-[3px]"
      style={{ backgroundColor: color }}
    />
  );
}

interface TreeNodeProps {
  node: FileTreeNode;
  allNodes: FileTreeNode[];
  depth: number;
  selectedFile: FileTreeNode | null;
  onFileSelect: (file: FileTreeNode) => void;
}

function TreeNode({ node, allNodes, depth, selectedFile, onFileSelect }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);

  const children = allNodes.filter((n) => {
    const parentPath = n.path.split('/').slice(0, -1).join('/');
    return parentPath === node.path && n.path !== node.path;
  });

  const isSelected = selectedFile?.path === node.path;
  const indent = depth * 12;

  if (node.type === 'directory') {
    return (
      <div>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="w-full flex items-center gap-1.5 px-2 py-1 hover:bg-terminal-surface text-terminal-muted hover:text-terminal-text transition-colors rounded text-xs"
          style={{ paddingLeft: `${8 + indent}px` }}
        >
          <span className="shrink-0 text-terminal-muted">
            {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
          </span>
          {expanded
            ? <FolderOpen size={13} className="shrink-0 text-terminal-yellow" />
            : <Folder size={13} className="shrink-0 text-terminal-yellow" />
          }
          <span className="truncate font-mono">{node.name}</span>
        </button>
        {expanded && children.map((child) => (
          <TreeNode
            key={child.path}
            node={child}
            allNodes={allNodes}
            depth={depth + 1}
            selectedFile={selectedFile}
            onFileSelect={onFileSelect}
          />
        ))}
      </div>
    );
  }

  return (
    <button
      onClick={() => onFileSelect(node)}
      className={`w-full flex items-center gap-1.5 px-2 py-1 rounded transition-colors text-xs group ${
        isSelected
          ? 'bg-terminal-accent/10 text-terminal-accent border-r-2 border-terminal-accent'
          : 'text-terminal-muted hover:bg-terminal-surface hover:text-terminal-text'
      }`}
      style={{ paddingLeft: `${8 + indent}px` }}
      title={node.path}
    >
      <FileIcon language={node.language} />
      <span className="truncate font-mono">{node.name}</span>
      {node.lines && (
        <span className="ml-auto shrink-0 text-terminal-border text-[10px] opacity-0 group-hover:opacity-100 pr-1">
          {node.lines}
        </span>
      )}
    </button>
  );
}

export function FileExplorer({ fileTree, selectedFile, onFileSelect }: Props) {
  const [search, setSearch] = useState('');

  const filtered = search
    ? fileTree.filter(
        (n) =>
          n.type === 'file' &&
          n.name.toLowerCase().includes(search.toLowerCase())
      )
    : null;

  // Top-level nodes (no slash in path, or depth 0)
  const rootNodes = fileTree.filter((n) => !n.path.includes('/'));

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-terminal-border">
        <p className="text-[10px] font-mono uppercase tracking-widest text-terminal-muted mb-2">
          Explorer
        </p>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search files..."
          className="input-field w-full text-xs py-1"
        />
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1 px-1">
        {search && filtered ? (
          filtered.length === 0 ? (
            <p className="text-terminal-muted text-xs px-3 py-4 text-center">No files found</p>
          ) : (
            filtered.map((node) => (
              <button
                key={node.path}
                onClick={() => onFileSelect(node)}
                className={`w-full flex items-center gap-2 px-2 py-1 rounded text-xs transition-colors ${
                  selectedFile?.path === node.path
                    ? 'bg-terminal-accent/10 text-terminal-accent'
                    : 'text-terminal-muted hover:bg-terminal-surface hover:text-terminal-text'
                }`}
              >
                <FileIcon language={node.language} />
                <span className="truncate font-mono">{node.path}</span>
              </button>
            ))
          )
        ) : (
          rootNodes.map((node) => (
            <TreeNode
              key={node.path}
              node={node}
              allNodes={fileTree}
              depth={0}
              selectedFile={selectedFile}
              onFileSelect={onFileSelect}
            />
          ))
        )}
      </div>

      {/* Footer stats */}
      <div className="px-3 py-2 border-t border-terminal-border">
        <p className="text-[10px] text-terminal-muted font-mono">
          {fileTree.filter((n) => n.type === 'file').length} files indexed
        </p>
      </div>
    </div>
  );
}
