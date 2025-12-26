'use client';

import { useState, useEffect } from 'react';
import type { PlanResponse, SectionOutline } from '@/lib/types';
import { MessageSquare, X } from 'lucide-react';

interface SectionComment {
    sectionIndex: number;
    sectionTitle: string;
    comment: string;
}

interface CommentPopupProps {
    sectionTitle: string;
    existingComment?: string;
    onSubmit: (comment: string) => void;
    onClose: () => void;
}

// CommentPopup component with absolute positioning
function CommentPopup({ sectionTitle, existingComment, onSubmit, onClose, anchorRect }: CommentPopupProps & { anchorRect: DOMRect }) {
    const [comment, setComment] = useState(existingComment || '');
    const [style, setStyle] = useState<React.CSSProperties>({});

    useEffect(() => {
        // Calculate position relative to viewport but aligned with anchor
        // Default to showing below the button, aligned to right
        const top = anchorRect.bottom + window.scrollY + 8;
        const right = window.innerWidth - anchorRect.right - window.scrollX;

        setStyle({
            position: 'absolute',
            top: `${top}px`,
            right: `${20}px`, // Fixed margin from right side of screen
            zIndex: 1000,
        });

        // Close on escape
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', handleEsc);
        return () => document.removeEventListener('keydown', handleEsc);
    }, [anchorRect, onClose]);

    const handleSubmit = () => {
        if (comment.trim()) {
            onSubmit(comment.trim());
        }
    };

    return (
        <>
            <div className="comment-popup-backdrop" onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 999 }} />
            <div className="comment-popup" style={style}>
                <div className="comment-popup-header">
                    <h3 className="comment-popup-title">Add Comment</h3>
                    <button className="comment-popup-close" onClick={onClose}>
                        <X size={16} />
                    </button>
                </div>
                <div className="comment-popup-section">
                    Section: <strong>{sectionTitle}</strong>
                </div>
                <textarea
                    className="comment-textarea"
                    placeholder="Enter your feedback..."
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    autoFocus
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                            handleSubmit();
                        }
                    }}
                />
                <div className="comment-popup-actions">
                    <button className="comment-cancel-btn" onClick={onClose}>
                        Cancel
                    </button>
                    <button className="comment-submit-btn" onClick={handleSubmit}>
                        Add Comment
                    </button>
                </div>
            </div>
        </>
    );
}

interface PlanViewerProps {
    plan: PlanResponse;
    onApprove: (comments: SectionComment[]) => void;
    onAddFeedback: (comments: SectionComment[]) => void;
    disabled?: boolean;
    actions?: React.ReactNode;
}

export default function PlanViewer({ plan, onApprove, onAddFeedback, disabled, actions }: PlanViewerProps) {
    const [sectionComments, setSectionComments] = useState<Map<number, SectionComment>>(new Map());
    const [activeCommentSection, setActiveCommentSection] = useState<number | null>(null);
    const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);

    const handleCommentClick = (index: number, e: React.MouseEvent) => {
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        setAnchorRect(rect);
        setActiveCommentSection(index);
    };

    const handleAddComment = (sectionIndex: number, sectionTitle: string, comment: string) => {
        const newComments = new Map(sectionComments);
        newComments.set(sectionIndex, { sectionIndex, sectionTitle, comment });
        setSectionComments(newComments);
        setActiveCommentSection(null);
        setAnchorRect(null);
    };

    // ... helper functions handleApprove and handleFeedback remain same ...

    return (
        <>
            <div className="plan-viewer">
                {/* ... Header remains same ... */}
                <div className="plan-header">
                    <h2 className="plan-title">{plan.title}</h2>
                    <span className="plan-status">{plan.status.replace('_', ' ')}</span>
                </div>

                <div className="plan-sections">
                    {plan.sections.map((section, index) => (
                        <div key={index} className="plan-section">
                            {/* ... Section display remains same ... */}
                            <div className="section-header">
                                <div>
                                    <h3 className="section-title">
                                        {index + 1}. {section.title}
                                    </h3>
                                    <p className="section-description">{section.description}</p>
                                    {section.subsections.length > 0 && (
                                        <ul className="section-subsections">
                                            {section.subsections.map((sub, subIdx) => (
                                                <li key={subIdx}>{sub}</li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            </div>

                            <button
                                className={`section-comment-btn ${sectionComments.has(index) ? 'has-comment' : ''}`}
                                onClick={(e) => handleCommentClick(index, e)}
                            >
                                <MessageSquare size={14} />
                                {sectionComments.has(index) ? 'Edit' : 'Comment'}
                            </button>

                            {sectionComments.has(index) && (
                                <div className="section-comment">
                                    <div className="section-comment-label">Your comment:</div>
                                    {sectionComments.get(index)?.comment}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {actions && (
                    <div className="plan-actions-footer">
                        {actions}
                    </div>
                )}
            </div>

            {activeCommentSection !== null && anchorRect && (
                <CommentPopup
                    sectionTitle={plan.sections[activeCommentSection].title}
                    existingComment={sectionComments.get(activeCommentSection)?.comment}
                    onSubmit={(comment) =>
                        handleAddComment(activeCommentSection, plan.sections[activeCommentSection].title, comment)
                    }
                    onClose={() => {
                        setActiveCommentSection(null);
                        setAnchorRect(null);
                    }}
                    anchorRect={anchorRect}
                />
            )}
        </>
    );
}

export type { SectionComment };
