'use client';

import { useState, useCallback } from 'react';
import { ChatMessage, DocumentType, PlanStatus } from '@/lib/types';
import api from '@/lib/api';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

function generateId(): string {
    return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

export default function ChatContainer() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [activePlan, setActivePlan] = useState<string | null>(null);

    const addMessage = useCallback((role: ChatMessage['role'], content: string, metadata?: ChatMessage['metadata']) => {
        const message: ChatMessage = {
            id: generateId(),
            role,
            content,
            timestamp: new Date(),
            metadata,
        };
        setMessages((prev) => [...prev, message]);
        return message.id;
    }, []);

    const updateMessage = useCallback((id: string, updates: Partial<ChatMessage>) => {
        setMessages((prev) =>
            prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
        );
    }, []);

    const handleSend = async (
        message: string,
        options?: {
            documentType?: DocumentType;
            createPlan?: boolean;
            context?: string;
        }
    ) => {
        // Add user message
        addMessage('user', message, { documentType: options?.documentType });

        // Add loading assistant message
        const assistantId = addMessage('assistant', '', { isLoading: true });
        setIsLoading(true);

        try {
            if (options?.createPlan) {
                // Planning workflow
                const plan = await api.createPlan(message);
                setActivePlan(plan.plan_id);

                const planContent = formatPlanResponse(plan);
                updateMessage(assistantId, {
                    content: planContent,
                    metadata: { isLoading: false, planId: plan.plan_id },
                });
            } else {
                // Direct generation
                const result = await api.generateDocument({
                    document_type: options?.documentType || DocumentType.SRS,
                    requirements: message,
                    additional_context: options?.context,
                });

                updateMessage(assistantId, {
                    content: result.content,
                    metadata: { isLoading: false, documentType: result.document_type },
                });
            }
        } catch (error) {
            updateMessage(assistantId, {
                content: '',
                metadata: {
                    isLoading: false,
                    error: error instanceof Error ? error.message : 'An error occurred',
                },
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handlePlanAction = async (action: 'approve' | 'comment' | 'generate', comment?: string) => {
        if (!activePlan) return;

        const assistantId = addMessage('assistant', '', { isLoading: true });
        setIsLoading(true);

        try {
            let plan;
            switch (action) {
                case 'comment':
                    if (comment) {
                        addMessage('user', comment);
                        plan = await api.addComment(activePlan, comment);
                    }
                    break;
                case 'approve':
                    await api.approvePlan(activePlan);
                    plan = await api.generateFromPlan(activePlan);
                    if (plan.status === PlanStatus.COMPLETED && plan.final_document) {
                        updateMessage(assistantId, {
                            content: plan.final_document,
                            metadata: { isLoading: false },
                        });
                        setActivePlan(null);
                        return;
                    }
                    break;
                case 'generate':
                    plan = await api.generateFromPlan(activePlan);
                    if (plan.final_document) {
                        updateMessage(assistantId, {
                            content: plan.final_document,
                            metadata: { isLoading: false },
                        });
                        setActivePlan(null);
                        return;
                    }
                    break;
            }

            if (plan) {
                updateMessage(assistantId, {
                    content: formatPlanResponse(plan),
                    metadata: { isLoading: false, planId: plan.plan_id },
                });
            }
        } catch (error) {
            updateMessage(assistantId, {
                content: '',
                metadata: {
                    isLoading: false,
                    error: error instanceof Error ? error.message : 'Plan action failed',
                },
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-container">
            <MessageList messages={messages} />

            {activePlan && (
                <div className="plan-actions">
                    <button onClick={() => handlePlanAction('approve')} disabled={isLoading}>
                        ✅ Approve & Generate
                    </button>
                    <button
                        onClick={() => {
                            const comment = prompt('Enter your feedback:');
                            if (comment) handlePlanAction('comment', comment);
                        }}
                        disabled={isLoading}
                    >
                        💬 Add Feedback
                    </button>
                </div>
            )}

            <ChatInput onSend={handleSend} disabled={isLoading} />
        </div>
    );
}

function formatPlanResponse(plan: { title: string; sections: Array<{ title: string; description: string; subsections: string[] }>; status: string }) {
    let content = `## 📋 Document Plan: ${plan.title}\n\n`;
    content += `**Status:** ${plan.status.replace('_', ' ')}\n\n`;
    content += `### Proposed Outline\n\n`;

    plan.sections.forEach((section, i) => {
        content += `**${i + 1}. ${section.title}**\n`;
        content += `${section.description}\n`;
        if (section.subsections.length > 0) {
            section.subsections.forEach((sub) => {
                content += `  - ${sub}\n`;
            });
        }
        content += '\n';
    });

    content += `\n---\n*Use the buttons below to approve or provide feedback.*`;
    return content;
}
