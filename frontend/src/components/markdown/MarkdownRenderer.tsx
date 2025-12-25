'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import MermaidChart from './MermaidChart';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
    return (
        <div className={`markdown-body ${className}`}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    // Code block handling with Mermaid support
                    code({ className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                        const codeContent = String(children).replace(/\n$/, '');

                        // Handle Mermaid diagrams
                        if (language === 'mermaid') {
                            return <MermaidChart chart={codeContent} />;
                        }

                        // Inline code
                        if (!match) {
                            return (
                                <code className="inline-code" {...props}>
                                    {children}
                                </code>
                            );
                        }

                        // Syntax highlighted code blocks
                        return (
                            <div className="code-block-wrapper">
                                <div className="code-header">
                                    <span className="code-language">{language}</span>
                                    <button
                                        className="copy-button"
                                        onClick={() => navigator.clipboard.writeText(codeContent)}
                                        title="Copy code"
                                    >
                                        📋
                                    </button>
                                </div>
                                <SyntaxHighlighter
                                    style={oneDark}
                                    language={language}
                                    PreTag="div"
                                    customStyle={{
                                        margin: 0,
                                        borderRadius: '0 0 8px 8px',
                                        fontSize: '0.9rem',
                                    }}
                                >
                                    {codeContent}
                                </SyntaxHighlighter>
                            </div>
                        );
                    },

                    // Enhanced image handling
                    img({ src, alt, ...props }) {
                        return (
                            <figure className="image-figure">
                                <img
                                    src={src}
                                    alt={alt || 'Image'}
                                    loading="lazy"
                                    className="markdown-image"
                                    {...props}
                                />
                                {alt && <figcaption>{alt}</figcaption>}
                            </figure>
                        );
                    },

                    // Enhanced table styling
                    table({ children, ...props }) {
                        return (
                            <div className="table-wrapper">
                                <table {...props}>{children}</table>
                            </div>
                        );
                    },

                    // Enhanced blockquote
                    blockquote({ children, ...props }) {
                        return (
                            <blockquote className="enhanced-blockquote" {...props}>
                                {children}
                            </blockquote>
                        );
                    },

                    // Links open in new tab
                    a({ href, children, ...props }) {
                        const isExternal = href?.startsWith('http');
                        return (
                            <a
                                href={href}
                                target={isExternal ? '_blank' : undefined}
                                rel={isExternal ? 'noopener noreferrer' : undefined}
                                {...props}
                            >
                                {children}
                            </a>
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
