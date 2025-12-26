'use client';

import { useRef, useEffect } from 'react';
import type { ChatMessage, PlanResponse } from '@/lib/types';
import MessageItem from './MessageItem';
import PlanViewer, { SectionComment } from './PlanViewer';
import { Check, MessageSquare } from 'lucide-react';

interface MessageListProps {
    messages: ChatMessage[];
    activePlanData?: PlanResponse | null;
    isLoading?: boolean;
    onApprove?: (comments: SectionComment[]) => void;
    onFeedback?: (comments: SectionComment[]) => void;
    onGeneralFeedback?: (comment: string) => void;
}

export default function MessageList({
    messages,
    activePlanData,
    isLoading,
    onApprove,
    onFeedback,
    onGeneralFeedback
}: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, activePlanData]);

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

    // Find the message that triggered the plan (has planId in metadata)
    const planMessageIndex = messages.findIndex(msg => msg.metadata?.planId && !msg.metadata?.approvedPlan);

    return (
        <div className="message-list">
            {messages.map((message, index) => (
                <div key={message.id}>
                    <MessageItem message={message} />

                    {/* Render PlanViewer inline right after the message that triggered it */}
                    {index === planMessageIndex && activePlanData && (
                        <div className="plan-viewer-inline">
                            <PlanViewer
                                plan={activePlanData}
                                onApprove={onApprove || (() => { })}
                                onAddFeedback={onFeedback || (() => { })}
                                disabled={isLoading}
                                actions={
                                    <div className="plan-actions">
                                        <button
                                            onClick={() => onApprove && onApprove([])}
                                            disabled={isLoading}
                                            className="action-btn primary"
                                        >
                                            <Check size={16} /> Approve & Generate
                                        </button>
                                        <button
                                            onClick={() => {
                                                const comment = prompt('Enter general feedback (or use inline comments above):');
                                                if (comment && onGeneralFeedback) onGeneralFeedback(comment);
                                            }}
                                            disabled={isLoading}
                                            className="action-btn secondary"
                                        >
                                            <MessageSquare size={16} /> General Feedback
                                        </button>
                                    </div>
                                }
                            />
                        </div>
                    )}
                </div>
            ))}
            <div ref={bottomRef} />
        </div>
    );
}
