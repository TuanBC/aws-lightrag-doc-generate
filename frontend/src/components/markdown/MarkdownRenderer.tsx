'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSlug from 'rehype-slug';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import MermaidChart from './MermaidChart';
import { Copy, Check } from 'lucide-react';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

// Copy button with feedback animation
function CopyButton({ code }: { code: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button
            className="copy-button"
            onClick={handleCopy}
            title={copied ? "Copied!" : "Copy code"}
        >
            {copied ? <Check size={16} /> : <Copy size={16} />}
        </button>
    );
}

// Code block wrapper component
function CodeBlock({ language, code }: { language: string; code: string }) {
    return (
        <div className="code-block-wrapper">
            <div className="code-header">
                <span className="code-language">{language}</span>
                <CopyButton code={code} />
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
                {code}
            </SyntaxHighlighter>
        </div>
    );
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
    // Handle smooth scroll for anchor links
    const handleLinkClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
        if (href.startsWith('#')) {
            e.preventDefault();
            const targetId = href.slice(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    };

    return (
        <div className={`markdown-body ${className}`}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSlug]}
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
                        return <CodeBlock language={language} code={codeContent} />;
                    },

                    // Headings with IDs for anchor links
                    h1({ children, id, ...props }) {
                        return <h1 id={id} {...props}>{children}</h1>;
                    },
                    h2({ children, id, ...props }) {
                        return <h2 id={id} {...props}>{children}</h2>;
                    },
                    h3({ children, id, ...props }) {
                        return <h3 id={id} {...props}>{children}</h3>;
                    },
                    h4({ children, id, ...props }) {
                        return <h4 id={id} {...props}>{children}</h4>;
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

                    // Links with smooth scroll for anchors
                    a({ href, children, ...props }) {
                        const isAnchor = href?.startsWith('#');
                        const isExternal = href?.startsWith('http');

                        return (
                            <a
                                href={href}
                                onClick={isAnchor ? (e) => handleLinkClick(e, href!) : undefined}
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
