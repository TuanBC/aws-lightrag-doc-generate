'use client';

import { useRef, useState, DragEvent, ChangeEvent, ReactNode } from 'react';
import { Upload, X, FileText } from 'lucide-react';

interface FileUploadProps {
    onFileSelect: (file: { name: string; content: string }) => void;
    disabled?: boolean;
    compact?: boolean;
    triggerIcon?: ReactNode;
}

export default function FileUpload({ onFileSelect, disabled = false, compact = false, triggerIcon }: FileUploadProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [fileName, setFileName] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleFile = async (file: File) => {
        if (!file.name.endsWith('.md') && !file.name.endsWith('.markdown')) {
            setError('Markdown files only');
            setTimeout(() => setError(null), 3000);
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            setError('Max 5MB');
            setTimeout(() => setError(null), 3000);
            return;
        }

        try {
            const content = await file.text();
            setFileName(file.name);
            setError(null);
            onFileSelect({ name: file.name, content });
        } catch {
            setError('Read failed');
        }
    };

    const handleDrop = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    };

    return (
        <div className={`file-upload-wrapper ${compact ? 'compact' : ''}`}>
            <input
                ref={inputRef}
                type="file"
                accept=".md,.markdown"
                onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFile(file);
                }}
                className="hidden-input"
                disabled={disabled}
            />

            {triggerIcon ? (
                <button
                    type="button"
                    className="icon-button"
                    onClick={() => inputRef.current?.click()}
                    title="Upload context"
                >
                    {triggerIcon}
                </button>
            ) : (
                <div
                    className={`drop-zone ${isDragging ? 'dragging' : ''} ${fileName ? 'has-file' : ''}`}
                    onDrop={handleDrop}
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={() => setIsDragging(false)}
                    onClick={() => !fileName && inputRef.current?.click()}
                >
                    {fileName ? (
                        <div className="file-info-chip">
                            <FileText size={14} />
                            <span className="truncate-name">{fileName}</span>
                            <button
                                onClick={(e) => { e.stopPropagation(); setFileName(null); if (inputRef.current) inputRef.current.value = ''; }}
                                className="remove-btn"
                            >
                                <X size={12} />
                            </button>
                        </div>
                    ) : (
                        <div className="drop-prompt-clean">
                            <Upload size={24} className="upload-icon-faded" />
                            <span>Upload Context</span>
                        </div>
                    )}
                </div>
            )}

            {error && <div className="toast-error">{error}</div>}
        </div>
    );
}
