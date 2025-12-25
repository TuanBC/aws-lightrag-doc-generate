'use client';

import { useRef, useEffect } from 'react';
import type { ChatMessage } from '@/lib/types';
import MessageItem from './MessageItem';

interface MessageListProps {
    messages: ChatMessage[];
}

export default function MessageList({ messages }: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    if (messages.length === 0) {
        return (
            <div className="empty-chat">
                <div className="empty-icon">📝</div>
                <h3>Welcome to Technical Doc Generator</h3>
                <p>Generate SRS, API docs, architecture diagrams, and more.</p>
                <div className="quick-actions">
                    <div className="quick-action-item">
                        <span className="action-icon">🚀</span>
                        <div>
                            <strong>Quick Generate</strong>
                            <p>Describe what document you need</p>
                        </div>
                    </div>
                    <div className="quick-action-item">
                        <span className="action-icon">📋</span>
                        <div>
                            <strong>Custom Plan</strong>
                            <p>Create an outline first, then generate</p>
                        </div>
                    </div>
                    <div className="quick-action-item">
                        <span className="action-icon">📁</span>
                        <div>
                            <strong>Upload Context</strong>
                            <p>Add markdown files as context</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="message-list">
            {messages.map((message) => (
                <MessageItem key={message.id} message={message} />
            ))}
            <div ref={bottomRef} />
        </div>
    );
}
