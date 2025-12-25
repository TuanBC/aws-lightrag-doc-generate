'use client';

import { useState, KeyboardEvent, FormEvent } from 'react';
import { DocumentType } from '@/lib/types';
import FileUpload from './FileUpload';

interface ChatInputProps {
    onSend: (message: string, options?: {
        documentType?: DocumentType;
        createPlan?: boolean;
        context?: string;
    }) => void;
    disabled?: boolean;
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
    const [message, setMessage] = useState('');
    const [showOptions, setShowOptions] = useState(false);
    const [documentType, setDocumentType] = useState<DocumentType>(DocumentType.SRS);
    const [createPlan, setCreatePlan] = useState(false);
    const [contextFile, setContextFile] = useState<{ name: string; content: string } | null>(null);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if (!message.trim() || disabled) return;

        onSend(message, {
            documentType,
            createPlan,
            context: contextFile?.content,
        });

        setMessage('');
        setContextFile(null);
        setCreatePlan(false);
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <div className="chat-input-container">
            {showOptions && (
                <div className="input-options">
                    <div className="option-group">
                        <label htmlFor="doc-type">Document Type</label>
                        <select
                            id="doc-type"
                            value={documentType}
                            onChange={(e) => setDocumentType(e.target.value as DocumentType)}
                            disabled={disabled}
                        >
                            <option value={DocumentType.SRS}>Software Requirements Spec</option>
                            <option value={DocumentType.FUNCTIONAL_SPEC}>Functional Specification</option>
                            <option value={DocumentType.API_DOCS}>API Documentation</option>
                            <option value={DocumentType.ARCHITECTURE}>Architecture Document</option>
                        </select>
                    </div>

                    <div className="option-group checkbox-group">
                        <label>
                            <input
                                type="checkbox"
                                checked={createPlan}
                                onChange={(e) => setCreatePlan(e.target.checked)}
                                disabled={disabled}
                            />
                            <span>Create plan first (review before generating)</span>
                        </label>
                    </div>

                    <div className="option-group">
                        <label>Context File</label>
                        <FileUpload
                            onFileSelect={setContextFile}
                            disabled={disabled}
                        />
                    </div>
                </div>
            )}

            <form onSubmit={handleSubmit} className="input-form">
                <button
                    type="button"
                    className={`options-toggle ${showOptions ? 'active' : ''}`}
                    onClick={() => setShowOptions(!showOptions)}
                    title="Toggle options"
                >
                    ⚙️
                </button>

                <div className="input-wrapper">
                    <textarea
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Describe the document you want to generate..."
                        disabled={disabled}
                        rows={1}
                    />

                    {contextFile && (
                        <div className="attached-file">
                            📎 {contextFile.name}
                            <button onClick={() => setContextFile(null)} title="Remove">×</button>
                        </div>
                    )}
                </div>

                <button
                    type="submit"
                    className="send-button"
                    disabled={!message.trim() || disabled}
                    title="Send"
                >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                    </svg>
                </button>
            </form>
        </div>
    );
}
