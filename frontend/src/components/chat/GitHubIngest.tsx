'use client';

import { useState } from 'react';
import { Github, Loader2, Check, AlertCircle } from 'lucide-react';
import api from '@/lib/api';
import type { GitIngestResponse } from '@/lib/types';

interface GitHubIngestProps {
    onIngested?: (url: string, summary: string) => void;
}

export default function GitHubIngest({ onIngested }: GitHubIngestProps) {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<GitIngestResponse | null>(null);

    const handleIngest = async () => {
        if (!url.trim() || !url.includes('github.com')) {
            setError('Please enter a valid GitHub URL');
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const response = await api.ingestGitHubRepo(url);
            setResult(response);
            onIngested?.(url, response.summary);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Ingestion failed');
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !loading && url.trim()) {
            handleIngest();
        }
    };

    return (
        <div className="github-ingest">
            <div className="github-ingest-header">
                <Github size={18} />
                <span>Ingest GitHub Repository</span>
            </div>
            <div className="github-ingest-input">
                <input
                    type="text"
                    placeholder="https://github.com/owner/repo"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                />
                <button
                    onClick={handleIngest}
                    disabled={loading || !url.trim()}
                    className="github-ingest-button"
                >
                    {loading ? <Loader2 className="animate-spin" size={16} /> : 'Ingest'}
                </button>
            </div>
            {error && (
                <div className="github-ingest-error">
                    <AlertCircle size={14} /> {error}
                </div>
            )}
            {result && (
                <div className="github-ingest-success">
                    <Check size={14} />
                    <div className="github-ingest-stats">
                        <span>{result.file_count} files</span>
                        <span>•</span>
                        <span>{result.total_tokens.toLocaleString()} tokens</span>
                        <span>•</span>
                        <span>{result.documents_inserted} docs indexed</span>
                    </div>
                </div>
            )}
        </div>
    );
}
