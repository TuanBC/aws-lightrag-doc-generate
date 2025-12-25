'use client';

import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidChartProps {
    chart: string;
}

// Initialize mermaid with dark theme
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
    fontFamily: 'Inter, system-ui, sans-serif',
});

export default function MermaidChart({ chart }: MermaidChartProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svg, setSvg] = useState<string>('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const renderChart = async () => {
            if (!containerRef.current || !chart.trim()) return;

            try {
                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
                const { svg } = await mermaid.render(id, chart.trim());
                setSvg(svg);
                setError(null);
            } catch (err) {
                console.error('Mermaid render error:', err);
                setError(err instanceof Error ? err.message : 'Failed to render chart');
            }
        };

        renderChart();
    }, [chart]);

    if (error) {
        return (
            <div className="mermaid-error">
                <div className="error-header">⚠️ Chart Syntax Error</div>
                <pre className="error-message">{error}</pre>
                <details>
                    <summary>Show raw code</summary>
                    <pre className="raw-code">{chart}</pre>
                </details>
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className="mermaid-container"
            dangerouslySetInnerHTML={{ __html: svg }}
        />
    );
}
