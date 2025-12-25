'use client';

import type { ChatMessage } from '@/lib/types';
import MarkdownRenderer from '../markdown/MarkdownRenderer';

interface MessageItemProps {
    message: ChatMessage;
}

export default function MessageItem({ message }: MessageItemProps) {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';

    return (
        <div className={`message-item ${message.role}`}>
            <div className="message-avatar">
                {isUser ? '👤' : isSystem ? '⚙️' : '🤖'}
            </div>

            <div className="message-content-wrapper">
                <div className="message-header">
                    <span className="message-role">
                        {isUser ? 'You' : isSystem ? 'System' : 'Assistant'}
                    </span>
                    <span className="message-time">
                        {message.timestamp.toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit'
                        })}
                    </span>
                </div>

                <div className="message-content">
                    {message.metadata?.isLoading ? (
                        <div className="loading-indicator">
                            <div className="loading-dots">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                            <span className="loading-text">Generating...</span>
                        </div>
                    ) : message.metadata?.error ? (
                        <div className="error-message">
                            <span className="error-icon">❌</span>
                            {message.metadata.error}
                        </div>
                    ) : isUser ? (
                        <p>{message.content}</p>
                    ) : (
                        <MarkdownRenderer content={message.content} />
                    )}
                </div>

                {message.metadata?.documentType && (
                    <div className="message-meta">
                        <span className="meta-badge">
                            📄 {message.metadata.documentType.replace('_', ' ').toUpperCase()}
                        </span>
                    </div>
                )}

                {message.metadata?.planId && (
                    <div className="message-meta">
                        <span className="meta-badge">
                            📋 Plan: {message.metadata.planId.slice(0, 8)}...
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
}
