'use client';

import { useState, useEffect } from 'react';
import { X, Github, Trash2, Loader2, RefreshCw, AlertCircle, Check, Database } from 'lucide-react';
import api from '@/lib/api';
import type { IndexedRepo, GitIngestResponse } from '@/lib/types';

interface RepoManagerProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function RepoManager({ isOpen, onClose }: RepoManagerProps) {
    const [repos, setRepos] = useState<IndexedRepo[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [newUrl, setNewUrl] = useState('');
    const [ingesting, setIngesting] = useState(false);
    const [ingestResult, setIngestResult] = useState<GitIngestResponse | null>(null);
    const [deletingUrl, setDeletingUrl] = useState<string | null>(null);

    // Load repos when modal opens
    useEffect(() => {
        if (isOpen) {
            loadRepos();
        }
    }, [isOpen]);

    const loadRepos = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.listGitHubRepos();
            setRepos(response.repos);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load repos');
        } finally {
            setLoading(false);
        }
    };

    const handleIngest = async () => {
        if (!newUrl.trim() || !newUrl.includes('github.com')) {
            setError('Please enter a valid GitHub URL');
            return;
        }

        setIngesting(true);
        setError(null);
        setIngestResult(null);

        try {
            const result = await api.ingestGitHubRepo(newUrl);
            setIngestResult(result);
            setNewUrl('');
            // Refresh repo list
            await loadRepos();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Ingestion failed');
        } finally {
            setIngesting(false);
        }
    };

    const handleDelete = async (githubUrl: string) => {
        setDeletingUrl(githubUrl);
        setError(null);

        try {
            await api.deleteGitHubRepo(githubUrl);
            // Remove from local state
            setRepos(repos.filter(r => r.github_url !== githubUrl));
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Delete failed');
        } finally {
            setDeletingUrl(null);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !ingesting && newUrl.trim()) {
            handleIngest();
        }
    };

    const formatTokens = (tokens: number) => {
        if (tokens >= 1000) {
            return `${(tokens / 1000).toFixed(1)}k`;
        }
        return tokens.toString();
    };

    const extractRepoName = (url: string) => {
        const match = url.match(/github\.com\/([^/]+\/[^/]+)/);
        return match ? match[1] : url;
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-container" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <div className="modal-title">
                        <Database size={20} />
                        <span>Knowledge Base Manager</span>
                    </div>
                    <button className="modal-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="modal-body">
                    {/* Add Repo Section */}
                    <div className="repo-add-section">
                        <div className="repo-add-input">
                            <Github size={18} className="input-icon" />
                            <input
                                type="text"
                                placeholder="Paste GitHub repository URL..."
                                value={newUrl}
                                onChange={(e) => setNewUrl(e.target.value)}
                                onKeyDown={handleKeyDown}
                                disabled={ingesting}
                            />
                            <button
                                onClick={handleIngest}
                                disabled={ingesting || !newUrl.trim()}
                                className="add-btn"
                            >
                                {ingesting ? (
                                    <Loader2 className="animate-spin" size={16} />
                                ) : (
                                    '+ Add'
                                )}
                            </button>
                        </div>
                        {ingestResult && (
                            <div className="ingest-success">
                                <Check size={14} />
                                <span>Added {ingestResult.file_count} files ({formatTokens(ingestResult.total_tokens)} tokens)</span>
                            </div>
                        )}
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="repo-error">
                            <AlertCircle size={14} />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Repos List */}
                    <div className="repos-section">
                        <div className="repos-header">
                            <span>Indexed Repositories</span>
                            <button className="refresh-btn" onClick={loadRepos} disabled={loading}>
                                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                            </button>
                        </div>

                        {loading ? (
                            <div className="repos-loading">
                                <Loader2 className="animate-spin" size={24} />
                                <span>Loading...</span>
                            </div>
                        ) : repos.length === 0 ? (
                            <div className="repos-empty">
                                <Github size={32} />
                                <span>No repositories indexed yet</span>
                                <span className="subtitle">Add a GitHub URL above to get started</span>
                            </div>
                        ) : (
                            <div className="repos-list">
                                {repos.map((repo) => (
                                    <div key={repo.github_url} className="repo-item">
                                        <div className="repo-info">
                                            <div className="repo-name">
                                                <Github size={16} />
                                                <span>{extractRepoName(repo.github_url)}</span>
                                            </div>
                                            <div className="repo-stats">
                                                <span>{repo.file_count} files</span>
                                                <span>•</span>
                                                <span>{formatTokens(repo.estimated_tokens)} tokens</span>
                                            </div>
                                        </div>
                                        <button
                                            className="delete-btn"
                                            onClick={() => handleDelete(repo.github_url)}
                                            disabled={deletingUrl === repo.github_url}
                                        >
                                            {deletingUrl === repo.github_url ? (
                                                <Loader2 className="animate-spin" size={16} />
                                            ) : (
                                                <Trash2 size={16} />
                                            )}
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <div className="modal-footer">
                    <span className="footer-stats">
                        {repos.length} {repos.length === 1 ? 'repository' : 'repositories'} •
                        {' '}{formatTokens(repos.reduce((sum, r) => sum + r.estimated_tokens, 0))} total tokens
                    </span>
                    <button className="done-btn" onClick={onClose}>
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
}
