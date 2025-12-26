'use client';

import { useState } from 'react';
import type { ChatMessage } from '@/lib/types';
import MarkdownRenderer from '../markdown/MarkdownRenderer';
import ToolStepCard from './ToolStepCard';
import { ChevronDown, ChevronRight, FileText, CheckCircle } from 'lucide-react';

interface MessageItemProps {
    message: ChatMessage;
}

// Collapsible approved plan dropdown component
function ApprovedPlanDropdown({ plan }: { plan: NonNullable<ChatMessage['metadata']>['approvedPlan'] }) {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!plan) return null;

    return (
        <div className="approved-plan-dropdown">
            <button
                className="approved-plan-header"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="approved-plan-left">
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    <FileText size={16} />
                    <span className="approved-plan-title">{plan.title}</span>
                </div>
                <div className="approved-plan-right">
                    <CheckCircle size={14} className="approved-icon" />
                    <span className="approved-badge">Approved</span>
                </div>
            </button>

            {isExpanded && (
                <div className="approved-plan-content">
                    {plan.sections.map((section, index) => (
                        <div key={index} className="approved-section">
                            <h4 className="approved-section-title">
                                {index + 1}. {section.title}
                            </h4>
                            <p className="approved-section-desc">{section.description}</p>
                            {section.subsections.length > 0 && (
                                <ul className="approved-subsections">
                                    {section.subsections.map((sub, subIdx) => (
                                        <li key={subIdx}>{sub}</li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function MessageItem({ message }: MessageItemProps) {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';
    const hasApprovedPlan = message.metadata?.approvedPlan;

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

                {/* Render tool steps above content */}
                {message.metadata?.steps && message.metadata.steps.length > 0 && (
                    <div className="message-steps">
                        {message.metadata.steps.map((step, idx) => (
                            <ToolStepCard key={idx} step={step} />
                        ))}
                    </div>
                )}

                {/* Render collapsible approved plan dropdown */}
                {hasApprovedPlan && (
                    <ApprovedPlanDropdown plan={message.metadata?.approvedPlan} />
                )}

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


            </div>
        </div>
    );
}
