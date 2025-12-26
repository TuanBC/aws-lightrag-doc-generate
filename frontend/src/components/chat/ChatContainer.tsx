'use client';

import { useState, useCallback, useEffect } from 'react';
import { ChatMessage, DocumentType, PlanStatus, ToolStep, PlanResponse } from '@/lib/types';
import api from '@/lib/api';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import PlanViewer, { SectionComment } from './PlanViewer';
import { Rocket, FileText, Server, MessageSquare, Check, Sparkles, Zap, Map } from 'lucide-react';

function generateId(): string {
    return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

interface ChatContainerProps {
    initialAction?: {
        type: DocumentType;
        message?: string;
        createPlan?: boolean;
    } | null;
}

export default function ChatContainer({ initialAction }: ChatContainerProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [activePlan, setActivePlan] = useState<string | null>(null);
    const [activePlanData, setActivePlanData] = useState<PlanResponse | null>(null);
    const [currentDocType, setCurrentDocType] = useState<DocumentType>(DocumentType.SRS);
    const [isGuidedMode, setIsGuidedMode] = useState(false);

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

    // Update message steps in-place (for streaming)
    const addStepToMessage = useCallback((id: string, step: ToolStep) => {
        setMessages((prev) =>
            prev.map((msg) => {
                if (msg.id !== id) return msg;
                const currentSteps = msg.metadata?.steps || [];
                // Update existing step or add new one
                const existingIdx = currentSteps.findIndex(
                    (s) => s.tool_name === step.tool_name && s.status === 'running'
                );
                if (existingIdx >= 0 && step.status === 'done') {
                    // Update the existing running step to done
                    const newSteps = [...currentSteps];
                    newSteps[existingIdx] = step;
                    return { ...msg, metadata: { ...msg.metadata, steps: newSteps } };
                } else if (step.status === 'running') {
                    // Add new running step
                    return { ...msg, metadata: { ...msg.metadata, steps: [...currentSteps, step] } };
                }
                return msg;
            })
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
        addMessage('user', message, { documentType: options?.documentType });
        const assistantId = addMessage('assistant', '', { isLoading: true, steps: [] });
        setIsLoading(true);

        try {
            if (options?.createPlan) {
                // Planning mode - use regular API
                const plan = await api.createPlan(message);
                setActivePlan(plan.plan_id);
                setActivePlanData(plan);  // Store full plan for PlanViewer
                updateMessage(assistantId, {
                    content: '',  // Content rendered by PlanViewer
                    metadata: { isLoading: false, planId: plan.plan_id },
                });
            } else {
                // Fast mode - use streaming API with tool steps
                await api.generateDocumentStream(
                    {
                        document_type: options?.documentType || DocumentType.SRS,
                        requirements: message,
                        additional_context: options?.context,
                    },
                    {
                        onStep: (step) => {
                            addStepToMessage(assistantId, step);
                        },
                        onContent: (response) => {
                            updateMessage(assistantId, {
                                content: response.content,
                                metadata: {
                                    isLoading: false,
                                    documentType: response.document_type,
                                    steps: response.steps,
                                },
                            });
                        },
                        onDone: () => {
                            setIsLoading(false);
                        },
                        onError: (error) => {
                            updateMessage(assistantId, {
                                content: '',
                                metadata: {
                                    isLoading: false,
                                    error,
                                },
                            });
                            setIsLoading(false);
                        },
                    }
                );
                return; // Don't set isLoading=false here, onDone handles it
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
            if (options?.createPlan) {
                setIsLoading(false);
            }
        }
    };

    useEffect(() => {
        if (initialAction) {
            setCurrentDocType(initialAction.type);
            if (initialAction.createPlan !== undefined) {
                setIsGuidedMode(initialAction.createPlan);
            }
            if (initialAction.message) {
                handleSend(initialAction.message, {
                    documentType: initialAction.type,
                    createPlan: initialAction.createPlan
                });
            }
        }
    }, [initialAction]);

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
                        setActivePlanData(plan);  // Update plan data
                    }
                    break;
                case 'approve':
                    // Store the current plan data for collapsed display
                    const planToStore = activePlanData;

                    // Find and update the message that has this planId
                    const planMsgId = messages.find(m => m.metadata?.planId === activePlan)?.id;
                    if (planMsgId && planToStore) {
                        updateMessage(planMsgId, {
                            metadata: {
                                ...messages.find(m => m.id === planMsgId)?.metadata,
                                approvedPlan: planToStore,
                                planId: undefined // Clear active planId
                            }
                        });
                    }

                    await api.approvePlan(activePlan);
                    plan = await api.generateFromPlan(activePlan);
                    if (plan.status === PlanStatus.COMPLETED && plan.final_document) {
                        updateMessage(assistantId, { content: plan.final_document, metadata: { isLoading: false } });
                        setActivePlan(null);
                        setActivePlanData(null);  // Clear plan data
                        return;
                    }
                    break;
                case 'generate':
                    plan = await api.generateFromPlan(activePlan);
                    if (plan.final_document) {
                        updateMessage(assistantId, { content: plan.final_document, metadata: { isLoading: false } });
                        setActivePlan(null);
                        setActivePlanData(null);  // Clear plan data
                        return;
                    }
                    break;
            }

            if (plan) {
                setActivePlanData(plan);  // Update plan data
                updateMessage(assistantId, {
                    content: '',
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

    // Handle approve with section comments from PlanViewer
    const handleApproveWithComments = async (comments: SectionComment[]) => {
        if (!activePlan) return;

        // Add all comments to plan first
        for (const { sectionTitle, comment } of comments) {
            const fullComment = `[${sectionTitle}] ${comment}`;
            await api.addComment(activePlan, fullComment);
        }

        // Then approve and generate
        handlePlanAction('approve');
    };

    // Handle feedback with section comments from PlanViewer
    const handleFeedbackWithComments = async (comments: SectionComment[]) => {
        if (!activePlan || comments.length === 0) return;

        // Combine all comments into a single feedback message
        const feedbackMessage = comments
            .map(({ sectionTitle, comment }) => `**${sectionTitle}:** ${comment}`)
            .join('\n\n');

        handlePlanAction('comment', feedbackMessage);
    };

    return (
        <div className="chat-container">
            {messages.length === 0 ? (
                <div className="empty-state">
                    <div className="welcome-header">
                        <span className="greeting">Hello there</span>
                        <h2>What would you like to build?</h2>
                    </div>

                    <div className="quick-actions">
                        <div className="action-card" onClick={() => {
                            setCurrentDocType(DocumentType.SRS);
                            setIsGuidedMode(false);
                        }}>
                            <div className="card-header-icon">
                                <Rocket size={20} />
                                <span className="mode-badge fast"><Zap size={10} /> Fast</span>
                            </div>
                            <h3>Quick SRS</h3>
                        </div>
                        <div className="action-card" onClick={() => {
                            setCurrentDocType(DocumentType.SRS);
                            setIsGuidedMode(true);
                        }}>
                            <div className="card-header-icon">
                                <Sparkles size={20} />
                                <span className="mode-badge planning"><Map size={10} /> Planning</span>
                            </div>
                            <h3>SRS with Plan</h3>
                        </div>
                        <div className="action-card" onClick={() => {
                            setCurrentDocType(DocumentType.API_DOCS);
                            setIsGuidedMode(false);
                        }}>
                            <div className="card-header-icon">
                                <Server size={20} />
                                <span className="mode-badge fast"><Zap size={10} /> Fast</span>
                            </div>
                            <h3>API Docs</h3>
                        </div>
                        <div className="action-card" onClick={() => {
                            setCurrentDocType(DocumentType.GENERAL);
                            setIsGuidedMode(false);
                        }}>
                            <div className="card-header-icon">
                                <FileText size={20} />
                                <span className="mode-badge fast"><Zap size={10} /> Fast</span>
                            </div>
                            <h3>General</h3>
                        </div>
                    </div>
                </div>
            ) : (
                <>
                    <MessageList
                        messages={messages}
                        activePlanData={activePlanData}
                        isLoading={isLoading}
                        onApprove={handleApproveWithComments}
                        onFeedback={handleFeedbackWithComments}
                        onGeneralFeedback={(comment: string) => handlePlanAction('comment', comment)}
                    />
                </>
            )}

            <ChatInput
                onSend={handleSend}
                disabled={isLoading}
                initialDocumentType={currentDocType}
                initialCreatePlan={isGuidedMode}
                onOptionChange={(type, plan) => {
                    setCurrentDocType(type);
                    setIsGuidedMode(plan);
                }}
            />
        </div>
    );
}

function formatPlanResponse(plan: { title: string; sections: Array<{ title: string; description: string; subsections: string[] }>; status: string }) {
    let content = `## Document Plan: ${plan.title}\n\n`;
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
