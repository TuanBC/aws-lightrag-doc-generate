// API Client for backend communication

import type {
    GenerateDocumentRequest,
    GeneratedDocumentResponse,
    ValidateDocumentRequest,
    CriticReportResponse,
    UploadDocumentRequest,
    UploadDocumentResponse,
    PlanResponse,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async fetch<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Document Generation
    async generateDocument(request: GenerateDocumentRequest): Promise<GeneratedDocumentResponse> {
        return this.fetch<GeneratedDocumentResponse>('/api/v1/documents/generate', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    async generateDocumentMarkdown(request: GenerateDocumentRequest): Promise<string> {
        const url = `${this.baseUrl}/api/v1/documents/generate/markdown`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.text();
    }

    // Streaming Document Generation with Tool Steps (SSE)
    // Falls back to regular generateDocument if streaming endpoint is not available
    async generateDocumentStream(
        request: GenerateDocumentRequest,
        callbacks: {
            onStep?: (step: import('./types').ToolStep) => void;
            onContent?: (response: GeneratedDocumentResponse) => void;
            onDone?: () => void;
            onError?: (error: string) => void;
        }
    ): Promise<void> {
        const url = `${this.baseUrl}/api/v1/documents/generate/stream`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(request),
            });

            // Fallback to regular API if streaming endpoint not available (404)
            if (response.status === 404) {
                console.log('Streaming endpoint not available, falling back to regular API');
                const result = await this.generateDocument(request);
                callbacks.onContent?.(result);
                callbacks.onDone?.();
                return;
            }

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Request failed' }));
                callbacks.onError?.(error.detail || `HTTP ${response.status}`);
                return;
            }

            const reader = response.body?.getReader();
            if (!reader) {
                callbacks.onError?.('Failed to get response stream');
                return;
            }

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const event = JSON.parse(line.slice(6)) as import('./types').StreamEvent;

                            switch (event.event_type) {
                                case 'step':
                                    if (event.step) callbacks.onStep?.(event.step);
                                    break;
                                case 'content':
                                    if (event.content_chunk) {
                                        const doc = JSON.parse(event.content_chunk) as GeneratedDocumentResponse;
                                        callbacks.onContent?.(doc);
                                    }
                                    break;
                                case 'done':
                                    callbacks.onDone?.();
                                    break;
                                case 'error':
                                    callbacks.onError?.(event.error || 'Unknown error');
                                    break;
                            }
                        } catch (e) {
                            console.error('Failed to parse SSE event:', e);
                        }
                    }
                }
            }
        } catch (e) {
            // Network error - fallback to regular API
            console.log('Streaming failed, falling back to regular API:', e);
            try {
                const result = await this.generateDocument(request);
                callbacks.onContent?.(result);
                callbacks.onDone?.();
            } catch (fallbackError) {
                callbacks.onError?.(fallbackError instanceof Error ? fallbackError.message : 'Generation failed');
            }
        }
    }

    // Document Validation
    async validateDocument(request: ValidateDocumentRequest): Promise<CriticReportResponse> {
        return this.fetch<CriticReportResponse>('/api/v1/documents/validate', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    // Document Upload
    async uploadDocument(request: UploadDocumentRequest): Promise<UploadDocumentResponse> {
        return this.fetch<UploadDocumentResponse>('/api/v1/documents/upload', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    // Planning Agent
    async createPlan(userRequest: string): Promise<PlanResponse> {
        const url = `${this.baseUrl}/api/v1/plans/create?user_request=${encodeURIComponent(userRequest)}`;
        const response = await fetch(url, { method: 'POST' });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    async getPlan(planId: string): Promise<PlanResponse> {
        return this.fetch<PlanResponse>(`/api/v1/plans/${planId}`);
    }

    async addComment(planId: string, comment: string): Promise<PlanResponse> {
        const url = `${this.baseUrl}/api/v1/plans/${planId}/comment?comment=${encodeURIComponent(comment)}`;
        const response = await fetch(url, { method: 'POST' });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    async approvePlan(planId: string): Promise<{ message: string; plan_id: string; status: string }> {
        return this.fetch(`/api/v1/plans/${planId}/approve`, { method: 'POST' });
    }

    async generateFromPlan(planId: string): Promise<PlanResponse> {
        return this.fetch<PlanResponse>(`/api/v1/plans/${planId}/generate`, { method: 'POST' });
    }

    // LightRAG
    async indexDocument(content: string, docId?: string): Promise<unknown> {
        const params = new URLSearchParams({ content });
        if (docId) params.append('doc_id', docId);
        return this.fetch(`/api/v1/lightrag/index?${params}`, { method: 'POST' });
    }

    async queryLightRAG(query: string, mode: string = 'hybrid', topK: number = 5): Promise<unknown> {
        const params = new URLSearchParams({ query, mode, top_k: String(topK) });
        return this.fetch(`/api/v1/lightrag/query?${params}`);
    }
}

export const api = new ApiClient();
export default api;
