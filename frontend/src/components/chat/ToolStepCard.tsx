'use client';

import { useState } from 'react';
import type { ToolStep } from '@/lib/types';
import { ChevronDown, ChevronUp, Wrench, Check, Loader2, AlertCircle } from 'lucide-react';

interface ToolStepCardProps {
    step: ToolStep;
}

export default function ToolStepCard({ step }: ToolStepCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    const getStatusIcon = () => {
        switch (step.status) {
            case 'running':
                return <Loader2 className="status-icon spinning" size={14} />;
            case 'done':
                return <Check className="status-icon done" size={14} />;
            case 'error':
                return <AlertCircle className="status-icon error" size={14} />;
            default:
                return <Wrench className="status-icon" size={14} />;
        }
    };

    const formatParams = (params: Record<string, unknown>) => {
        return Object.entries(params)
            .map(([key, value]) => `${key}: ${String(value)}`)
            .join(' | ');
    };

    return (
        <div className={`tool-step-card ${step.status}`}>
            <div
                className="tool-step-header"
                onClick={() => step.result_detail && setIsExpanded(!isExpanded)}
            >
                <div className="tool-step-left">
                    {getStatusIcon()}
                    <span className="tool-name">{step.tool_name}</span>
                    <span className="tool-params">{formatParams(step.parameters)}</span>
                </div>

                <div className="tool-step-right">
                    {step.result_summary && (
                        <span className="result-summary">{step.result_summary}</span>
                    )}
                    {step.result_detail && (
                        <button className="expand-btn">
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </button>
                    )}
                </div>
            </div>

            {isExpanded && step.result_detail && (
                <div className="tool-step-detail">
                    <pre>{step.result_detail}</pre>
                </div>
            )}
        </div>
    );
}
