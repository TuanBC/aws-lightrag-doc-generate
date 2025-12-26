'use client';

import { useState, useRef, useEffect } from 'react';
import { Download, FileText, FileType, ChevronDown } from 'lucide-react';
import { exportToMarkdown, exportToDocx } from '@/lib/exportUtils';

interface ExportDropdownProps {
    content: string;
    messageRef?: React.RefObject<HTMLElement>;
    title?: string;
}

export default function ExportDropdown({ content, messageRef, title }: ExportDropdownProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const generateFilename = (extension: string) => {
        const timestamp = new Date().toISOString().slice(0, 10);
        const safeName = title
            ? title.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 30)
            : 'document';
        return `${safeName}_${timestamp}.${extension}`;
    };

    const handleExportMarkdown = async () => {
        setIsExporting(true);
        try {
            await exportToMarkdown(content, generateFilename('md'));
        } finally {
            setIsExporting(false);
            setIsOpen(false);
        }
    };

    const handleExportDocx = async () => {
        setIsExporting(true);
        try {
            const element = messageRef?.current || undefined;
            await exportToDocx(content, generateFilename('docx'), element);
        } finally {
            setIsExporting(false);
            setIsOpen(false);
        }
    };

    return (
        <div className="export-dropdown" ref={dropdownRef}>
            <button
                className="export-button"
                onClick={() => setIsOpen(!isOpen)}
                disabled={isExporting}
                title="Export document"
            >
                <Download size={16} />
                <span>Export</span>
                <ChevronDown size={14} className={`chevron ${isOpen ? 'open' : ''}`} />
            </button>

            {isOpen && (
                <div className="export-menu">
                    <button
                        className="export-option"
                        onClick={handleExportMarkdown}
                        disabled={isExporting}
                    >
                        <FileText size={16} />
                        <span>Markdown (.md)</span>
                    </button>
                    <button
                        className="export-option"
                        onClick={handleExportDocx}
                        disabled={isExporting}
                    >
                        <FileType size={16} />
                        <span>Word Document (.docx)</span>
                    </button>
                </div>
            )}
        </div>
    );
}
