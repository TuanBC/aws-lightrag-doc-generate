'use client';

import { useRef, useState, DragEvent, ChangeEvent } from 'react';

interface FileUploadProps {
    onFileSelect: (file: { name: string; content: string }) => void;
    disabled?: boolean;
}

export default function FileUpload({ onFileSelect, disabled = false }: FileUploadProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [fileName, setFileName] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleFile = async (file: File) => {
        // Only allow markdown files
        if (!file.name.endsWith('.md') && !file.name.endsWith('.markdown')) {
            setError('Only markdown files (.md) are allowed');
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            setError('File size must be less than 5MB');
            return;
        }

        try {
            const content = await file.text();
            setFileName(file.name);
            setError(null);
            onFileSelect({ name: file.name, content });
        } catch {
            setError('Failed to read file');
        }
    };

    const handleDrop = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    };

    const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
    };

    const handleClick = () => {
        inputRef.current?.click();
    };

    const handleClear = () => {
        setFileName(null);
        setError(null);
        if (inputRef.current) inputRef.current.value = '';
    };

    return (
        <div className="file-upload-container">
            <input
                ref={inputRef}
                type="file"
                accept=".md,.markdown"
                onChange={handleInputChange}
                className="hidden-input"
                disabled={disabled}
            />

            <div
                className={`drop-zone ${isDragging ? 'dragging' : ''} ${fileName ? 'has-file' : ''} ${disabled ? 'disabled' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={!fileName ? handleClick : undefined}
            >
                {fileName ? (
                    <div className="file-info">
                        <span className="file-icon">📄</span>
                        <span className="file-name">{fileName}</span>
                        <button
                            className="clear-button"
                            onClick={(e) => { e.stopPropagation(); handleClear(); }}
                            title="Remove file"
                        >
                            ✕
                        </button>
                    </div>
                ) : (
                    <div className="drop-prompt">
                        <span className="upload-icon">📁</span>
                        <span>Drop markdown file here or click to browse</span>
                        <span className="file-hint">Only .md files allowed</span>
                    </div>
                )}
            </div>

            {error && <div className="upload-error">{error}</div>}
        </div>
    );
}
