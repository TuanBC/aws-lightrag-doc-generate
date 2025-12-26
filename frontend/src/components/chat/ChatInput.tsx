'use client';

import { useState, KeyboardEvent, FormEvent, useEffect, useRef } from 'react';
import { DocumentType } from '@/lib/types';
import FileUpload from './FileUpload';
import { Send, Paperclip, Zap, Map } from 'lucide-react';

interface ChatInputProps {
    onSend: (message: string, options?: {
        documentType?: DocumentType;
        createPlan?: boolean;
        context?: string;
    }) => void;
    disabled?: boolean;
    initialDocumentType?: DocumentType;
    initialCreatePlan?: boolean;
    onOptionChange?: (type: DocumentType, plan: boolean) => void;
}

const getPlaceholderText = (type: DocumentType, isPlan: boolean) => {
    const typeName = type === DocumentType.SRS ? 'SRS' : type.toLowerCase().replace(/_/g, ' ');

    if (type === DocumentType.GENERAL) {
        return isPlan ? "Describe the document you want to plan..." : "Describe the document you need...";
    }

    return isPlan
        ? `Describe goals for the ${typeName} plan...`
        : `Describe requirements for the ${typeName}...`;
};

export default function ChatInput({
    onSend,
    disabled = false,
    initialDocumentType = DocumentType.SRS,
    initialCreatePlan = false,
    onOptionChange
}: ChatInputProps) {
    const [message, setMessage] = useState('');
    const [documentType, setDocumentType] = useState<DocumentType>(initialDocumentType);
    const [createPlan, setCreatePlan] = useState(initialCreatePlan);
    const [contextFile, setContextFile] = useState<{ name: string; content: string } | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
        }
    }, [message]);

    // Sync with initial props (one-way: parent -> child)
    useEffect(() => {
        setDocumentType(initialDocumentType);
    }, [initialDocumentType]);

    useEffect(() => {
        setCreatePlan(initialCreatePlan);
    }, [initialCreatePlan]);

    // REMOVED: The problematic useEffect that called onOptionChange on every state change
    // This was causing infinite loops. Now we call onOptionChange only from explicit user actions.

    const handleModeChange = (isPlan: boolean) => {
        setCreatePlan(isPlan);
        onOptionChange?.(documentType, isPlan);
    };

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
        if (textareaRef.current) textareaRef.current.style.height = 'auto';
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <div className="chat-input-wrapper">
            <form onSubmit={handleSubmit} className="gemini-input-container">
                <div className="input-area-top">
                    <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={getPlaceholderText(documentType, createPlan)}
                        disabled={disabled}
                        rows={1}
                        className="gemini-textarea"
                    />
                    {contextFile && (
                        <div className="file-chip">
                            <Paperclip size={12} />
                            <span>{contextFile.name}</span>
                            <button onClick={() => setContextFile(null)} className="chip-remove">×</button>
                        </div>
                    )}
                </div>

                <div className="input-actions-bottom">
                    <div className="left-actions">
                        <div className="mode-pill-group">
                            <button
                                type="button"
                                className={`mode-pill-btn ${!createPlan ? 'active' : ''}`}
                                onClick={() => handleModeChange(false)}
                                title="Fast Generation: Execute directly"
                            >
                                <Zap size={14} />
                                <span>Fast</span>
                            </button>
                            <button
                                type="button"
                                className={`mode-pill-btn ${createPlan ? 'active' : ''}`}
                                onClick={() => handleModeChange(true)}
                                title="Planning Mode: Create an outline first"
                            >
                                <Map size={14} />
                                <span>Plan</span>
                            </button>
                        </div>
                    </div>

                    <div className="right-actions">
                        <div className="upload-trigger">
                            <FileUpload
                                onFileSelect={setContextFile}
                                disabled={disabled}
                                compact={true}
                                triggerIcon={<Paperclip size={20} />}
                            />
                        </div>

                        <button
                            type="submit"
                            className={`send-fab ${message.trim() ? 'ready' : ''}`}
                            disabled={!message.trim() || disabled}
                            title="Send"
                        >
                            <Send size={20} />
                        </button>
                    </div>
                </div>
            </form>

            <div className="input-footer">
                {/* Minimal footer since controls are inline now */}
            </div>
        </div>
    );
}
