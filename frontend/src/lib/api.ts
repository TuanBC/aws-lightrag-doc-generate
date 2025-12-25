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
