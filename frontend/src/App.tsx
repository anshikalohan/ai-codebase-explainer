import { useState, useCallback, useEffect } from 'react';
import { UploadPanel } from './components/UploadPanel';
import { MainWorkspace } from './components/MainWorkspace';
import type { Session, IngestResponse } from './utils/types';
import { getSession } from './utils/api';

type AppState = 'landing' | 'indexing' | 'ready';

export default function App() {
  const [appState, setAppState] = useState<AppState>('landing');
  const [session, setSession] = useState<Session | null>(null);
  const [ingestData, setIngestData] = useState<IngestResponse | null>(null);

  // Poll for indexing completion
  useEffect(() => {
    if (appState !== 'indexing' || !ingestData) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getSession(ingestData.session_id);
        setSession(updated);
        if (updated.indexing_complete && updated.chunks_indexed > 0) {
          setAppState('ready');
          clearInterval(interval);
        }
      } catch (err) {
        console.error('Session poll error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [appState, ingestData]);

  const handleIngestSuccess = useCallback((data: IngestResponse) => {
    setIngestData(data);
    setAppState('indexing');
    // Bootstrap session object immediately
    setSession({
      session_id: data.session_id,
      source: data.source_name.includes('github.com') ? 'github' : 'zip',
      source_name: data.source_name,
      stats: data.stats,
      file_tree: data.file_tree,
      indexing_complete: false,
      chunks_indexed: 0,
      chat_turns: 0,
    });
  }, []);

  const handleReset = useCallback(() => {
    setSession(null);
    setIngestData(null);
    setAppState('landing');
  }, []);

  if (appState === 'landing') {
    return <UploadPanel onSuccess={handleIngestSuccess} />;
  }

  return (
    <MainWorkspace
      session={session!}
      isIndexing={appState === 'indexing'}
      onReset={handleReset}
    />
  );
}
