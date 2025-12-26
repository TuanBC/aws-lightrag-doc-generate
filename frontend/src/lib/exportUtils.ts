'use client';

import { saveAs } from 'file-saver';
import { toPng } from 'html-to-image';
import {
    Document,
    Packer,
    Paragraph,
    TextRun,
    HeadingLevel,
    ImageRun,
    Table,
    TableRow,
    TableCell,
    WidthType,
    BorderStyle,
    AlignmentType,
    ExternalHyperlink,
    BookmarkStart,
    BookmarkEnd,
} from 'docx';

// ============================================
// File Save with Native Dialog
// ============================================

// Check if File System Access API is available
function supportsFileSystemAccess(): boolean {
    return 'showSaveFilePicker' in window;
}

// Save file with native dialog (File System Access API)
async function saveWithDialog(
    blob: Blob,
    suggestedName: string,
    accept: Record<string, string[]>
): Promise<boolean> {
    if (!supportsFileSystemAccess()) {
        return false;
    }

    try {
        const handle = await (window as typeof window & {
            showSaveFilePicker: (options: {
                suggestedName: string;
                types: Array<{ description: string; accept: Record<string, string[]> }>;
            }) => Promise<FileSystemFileHandle>;
        }).showSaveFilePicker({
            suggestedName,
            types: [
                {
                    description: Object.keys(accept)[0] || 'Document',
                    accept,
                },
            ],
        });

        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return true;
    } catch (error) {
        // User cancelled the dialog or other error
        if ((error as Error).name === 'AbortError') {
            return true; // User cancelled, don't fall back
        }
        console.error('Save dialog error:', error);
        return false;
    }
}

// ============================================
// Markdown Export
// ============================================

export async function exportToMarkdown(content: string, filename?: string): Promise<void> {
    const finalFilename = filename || `document_${Date.now()}.md`;
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });

    // Try native dialog first, fall back to auto-download
    const saved = await saveWithDialog(blob, finalFilename, {
        'text/markdown': ['.md'],
    });

    if (!saved) {
        saveAs(blob, finalFilename);
    }
}

// ============================================
// DOCX Export with Mermaid chart support
// ============================================

interface ParsedElement {
    type: 'heading' | 'paragraph' | 'code' | 'list' | 'table' | 'mermaid' | 'blockquote';
    level?: number;
    content: string;
    language?: string;
    items?: string[];
    rows?: string[][];
}

// Parse markdown into structured elements
function parseMarkdown(content: string): ParsedElement[] {
    const elements: ParsedElement[] = [];
    const lines = content.split('\n');
    let i = 0;

    while (i < lines.length) {
        const line = lines[i];

        // Headings
        const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
        if (headingMatch) {
            elements.push({
                type: 'heading',
                level: headingMatch[1].length,
                content: headingMatch[2],
            });
            i++;
            continue;
        }

        // Code blocks (including mermaid)
        if (line.startsWith('```')) {
            const language = line.slice(3).trim();
            const codeLines: string[] = [];
            i++;
            while (i < lines.length && !lines[i].startsWith('```')) {
                codeLines.push(lines[i]);
                i++;
            }
            i++; // Skip closing ```

            if (language === 'mermaid') {
                elements.push({
                    type: 'mermaid',
                    content: codeLines.join('\n'),
                });
            } else {
                elements.push({
                    type: 'code',
                    language: language || 'text',
                    content: codeLines.join('\n'),
                });
            }
            continue;
        }

        // Blockquotes
        if (line.startsWith('>')) {
            const quoteLines: string[] = [];
            while (i < lines.length && lines[i].startsWith('>')) {
                quoteLines.push(lines[i].replace(/^>\s*/, ''));
                i++;
            }
            elements.push({
                type: 'blockquote',
                content: quoteLines.join('\n'),
            });
            continue;
        }

        // Unordered lists
        if (line.match(/^[-*+]\s+/)) {
            const items: string[] = [];
            while (i < lines.length && lines[i].match(/^[-*+]\s+/)) {
                items.push(lines[i].replace(/^[-*+]\s+/, ''));
                i++;
            }
            elements.push({
                type: 'list',
                items,
                content: '',
            });
            continue;
        }

        // Ordered lists
        if (line.match(/^\d+\.\s+/)) {
            const items: string[] = [];
            while (i < lines.length && lines[i].match(/^\d+\.\s+/)) {
                items.push(lines[i].replace(/^\d+\.\s+/, ''));
                i++;
            }
            elements.push({
                type: 'list',
                items,
                content: '',
            });
            continue;
        }

        // Tables
        if (line.includes('|') && lines[i + 1]?.includes('---')) {
            const tableRows: string[][] = [];
            while (i < lines.length && lines[i].includes('|')) {
                if (!lines[i].includes('---')) {
                    const cells = lines[i]
                        .split('|')
                        .map(c => c.trim())
                        .filter(c => c.length > 0);
                    tableRows.push(cells);
                }
                i++;
            }
            elements.push({
                type: 'table',
                rows: tableRows,
                content: '',
            });
            continue;
        }

        // Regular paragraph
        if (line.trim()) {
            const paragraphLines: string[] = [];
            while (i < lines.length && lines[i].trim() && !lines[i].startsWith('#') && !lines[i].startsWith('```') && !lines[i].startsWith('>') && !lines[i].match(/^[-*+]\s+/) && !lines[i].match(/^\d+\.\s+/)) {
                paragraphLines.push(lines[i]);
                i++;
            }
            elements.push({
                type: 'paragraph',
                content: paragraphLines.join(' '),
            });
            continue;
        }

        i++;
    }

    return elements;
}

// Parse inline formatting (bold, italic, code, links)
type InlineElement = TextRun | ExternalHyperlink;

function parseInlineFormatting(text: string): InlineElement[] {
    const elements: InlineElement[] = [];

    // Regex to match links, bold, italic, inline code, and regular text
    const regex = /(\[([^\]]+)\]\(([^)]+)\))|(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)|([^[*`]+)/g;
    let match;

    while ((match = regex.exec(text)) !== null) {
        if (match[1]) {
            // Markdown link [text](url)
            const linkText = match[2];
            const linkUrl = match[3];

            // For internal anchors (#section), show as styled text
            if (linkUrl.startsWith('#')) {
                elements.push(new TextRun({
                    text: linkText,
                    color: '4285f4',
                    underline: { type: 'single' },
                }));
            } else {
                // External link - create hyperlink
                elements.push(new ExternalHyperlink({
                    children: [
                        new TextRun({
                            text: linkText,
                            color: '4285f4',
                            underline: { type: 'single' },
                        }),
                    ],
                    link: linkUrl,
                }));
            }
        } else if (match[5]) {
            // Bold **text**
            elements.push(new TextRun({ text: match[5], bold: true }));
        } else if (match[7]) {
            // Italic *text*
            elements.push(new TextRun({ text: match[7], italics: true }));
        } else if (match[9]) {
            // Inline code `text`
            elements.push(new TextRun({
                text: match[9],
                font: 'Consolas',
                shading: { fill: 'E8E8E8' },
            }));
        } else if (match[10]) {
            // Regular text
            elements.push(new TextRun({ text: match[10] }));
        }
    }

    return elements.length > 0 ? elements : [new TextRun({ text })];
}

// Convert heading level to docx HeadingLevel
function getHeadingLevel(level: number): (typeof HeadingLevel)[keyof typeof HeadingLevel] {
    const levels: Record<number, (typeof HeadingLevel)[keyof typeof HeadingLevel]> = {
        1: HeadingLevel.HEADING_1,
        2: HeadingLevel.HEADING_2,
        3: HeadingLevel.HEADING_3,
        4: HeadingLevel.HEADING_4,
        5: HeadingLevel.HEADING_5,
        6: HeadingLevel.HEADING_6,
    };
    return levels[level] || HeadingLevel.HEADING_1;
}

// Capture Mermaid charts from the DOM and return as image data
async function captureMermaidCharts(): Promise<Map<string, Uint8Array>> {
    const charts = new Map<string, Uint8Array>();
    const mermaidContainers = document.querySelectorAll('.mermaid-container');

    for (let i = 0; i < mermaidContainers.length; i++) {
        const container = mermaidContainers[i] as HTMLElement;
        try {
            const dataUrl = await toPng(container, {
                backgroundColor: '#1e1f20',
                pixelRatio: 2,
            });

            // Convert data URL to Uint8Array
            const response = await fetch(dataUrl);
            const blob = await response.blob();
            const arrayBuffer = await blob.arrayBuffer();
            charts.set(`mermaid_${i}`, new Uint8Array(arrayBuffer));
        } catch (error) {
            console.error('Failed to capture mermaid chart:', error);
        }
    }

    return charts;
}

export async function exportToDocx(
    content: string,
    filename?: string,
    messageElement?: HTMLElement
): Promise<void> {
    const finalFilename = filename || `document_${Date.now()}.docx`;
    const elements = parseMarkdown(content);

    // Capture any Mermaid charts from the rendered DOM
    const mermaidImages = messageElement
        ? await captureMermaidChartsFromElement(messageElement)
        : await captureMermaidCharts();

    let mermaidIndex = 0;
    const docElements: (Paragraph | Table)[] = [];

    for (const element of elements) {
        switch (element.type) {
            case 'heading':
                docElements.push(
                    new Paragraph({
                        heading: getHeadingLevel(element.level || 1),
                        children: parseInlineFormatting(element.content),
                        spacing: { before: 240, after: 120 },
                    })
                );
                break;

            case 'paragraph':
                docElements.push(
                    new Paragraph({
                        children: parseInlineFormatting(element.content),
                        spacing: { after: 120 },
                    })
                );
                break;

            case 'code':
                docElements.push(
                    new Paragraph({
                        children: [
                            new TextRun({
                                text: element.content,
                                font: 'Consolas',
                                size: 20,
                            }),
                        ],
                        shading: { fill: 'F5F5F5' },
                        spacing: { before: 120, after: 120 },
                    })
                );
                break;

            case 'mermaid':
                const imageData = mermaidImages.get(`mermaid_${mermaidIndex}`);
                if (imageData) {
                    docElements.push(
                        new Paragraph({
                            children: [
                                new ImageRun({
                                    data: imageData,
                                    transformation: {
                                        width: 500,
                                        height: 300,
                                    },
                                    type: 'png',
                                }),
                            ],
                            alignment: AlignmentType.CENTER,
                            spacing: { before: 240, after: 240 },
                        })
                    );
                    mermaidIndex++;
                } else {
                    // Fallback: include mermaid code as text
                    docElements.push(
                        new Paragraph({
                            children: [
                                new TextRun({
                                    text: '[Diagram: ' + element.content.split('\n')[0] + '...]',
                                    italics: true,
                                    color: '666666',
                                }),
                            ],
                            spacing: { before: 120, after: 120 },
                        })
                    );
                }
                break;

            case 'blockquote':
                docElements.push(
                    new Paragraph({
                        children: parseInlineFormatting(element.content),
                        indent: { left: 720 },
                        border: {
                            left: { style: BorderStyle.SINGLE, size: 24, color: '4285f4' },
                        },
                        spacing: { before: 120, after: 120 },
                    })
                );
                break;

            case 'list':
                if (element.items) {
                    for (const item of element.items) {
                        docElements.push(
                            new Paragraph({
                                children: [
                                    new TextRun({ text: '• ' }),
                                    ...parseInlineFormatting(item),
                                ],
                                indent: { left: 360 },
                            })
                        );
                    }
                }
                break;

            case 'table':
                if (element.rows && element.rows.length > 0) {
                    const tableRows = element.rows.map((row, rowIndex) =>
                        new TableRow({
                            children: row.map(cell =>
                                new TableCell({
                                    children: [
                                        new Paragraph({
                                            children: parseInlineFormatting(cell),
                                        }),
                                    ],
                                    shading: rowIndex === 0 ? { fill: 'E8E8E8' } : undefined,
                                })
                            ),
                        })
                    );

                    docElements.push(
                        new Table({
                            rows: tableRows,
                            width: { size: 100, type: WidthType.PERCENTAGE },
                        })
                    );
                }
                break;
        }
    }

    const doc = new Document({
        sections: [
            {
                children: docElements,
            },
        ],
    });

    const blob = await Packer.toBlob(doc);

    // Try native dialog first, fall back to auto-download
    const saved = await saveWithDialog(blob, finalFilename, {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    });

    if (!saved) {
        saveAs(blob, finalFilename);
    }
}

// Capture mermaid charts from a specific message element
async function captureMermaidChartsFromElement(element: HTMLElement): Promise<Map<string, Uint8Array>> {
    const charts = new Map<string, Uint8Array>();
    const mermaidContainers = element.querySelectorAll('.mermaid-container');

    for (let i = 0; i < mermaidContainers.length; i++) {
        const container = mermaidContainers[i] as HTMLElement;
        try {
            const dataUrl = await toPng(container, {
                backgroundColor: '#1e1f20',
                pixelRatio: 2,
            });

            const response = await fetch(dataUrl);
            const blob = await response.blob();
            const arrayBuffer = await blob.arrayBuffer();
            charts.set(`mermaid_${i}`, new Uint8Array(arrayBuffer));
        } catch (error) {
            console.error('Failed to capture mermaid chart:', error);
        }
    }

    return charts;
}
