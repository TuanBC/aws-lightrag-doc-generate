// API Types matching backend Pydantic schemas

export enum DocumentType {
    SRS = 'srs',
    FUNCTIONAL_SPEC = 'functional_spec',
    API_DOCS = 'api_docs',
    ARCHITECTURE = 'architecture',
}

export enum ValidationSeverity {
    ERROR = 'error',
    WARNING = 'warning',
    INFO = 'info',
}

export enum PlanStatus {
    PENDING_REVIEW = 'pending_review',
    APPROVED = 'approved',
    GENERATING = 'generating',
    COMPLETED = 'completed',
    FAILED = 'failed',
}

// Request Types
export interface GenerateDocumentRequest {
    document_type: DocumentType;
    library_name?: string;
    requirements?: string;
    topics?: string[];
    additional_context?: string;
}

export interface ValidateDocumentRequest {
    content: string;
    requirements?: string;
    check_content?: boolean;
}

export interface UploadDocumentRequest {
    content: string;
    filename?: string;
    metadata?: Record<string, string>;
}

// Response Types
export interface ValidationIssue {
    severity: ValidationSeverity;
    category: string;
    message: string;
    line_number?: number;
    suggestion?: string;
}

export interface ValidationResultResponse {
    passed: boolean;
    issues: ValidationIssue[];
    checked_items: number;
}

export interface CriticReportResponse {
    overall_passed: boolean;
    markdown_result: ValidationResultResponse;
    mermaid_result: ValidationResultResponse;
    content_result?: ValidationResultResponse;
    total_errors: number;
    total_warnings: number;
    suggestions: string[];
}

export interface GeneratedDocumentResponse {
    document_type: DocumentType;
    title: string;
    content: string;
    library_name?: string;
    topics: string[];
    generated_at: string;
    metadata: Record<string, unknown>;
}

export interface UploadDocumentResponse {
    document_id: string;
    s3_uri: string;
    message: string;
}

export interface SectionOutline {
    title: string;
    description: string;
    subsections: string[];
    estimated_length: string;
}

export interface PlanResponse {
    plan_id: string;
    status: PlanStatus;
    user_request: string;
    document_type: string;
    title: string;
    sections: SectionOutline[];
    created_at: string;
    updated_at: string;
    user_comments: string[];
    final_document?: string;
}

// Chat Types
export type MessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
    id: string;
    role: MessageRole;
    content: string;
    timestamp: Date;
    metadata?: {
        documentType?: DocumentType;
        planId?: string;
        isLoading?: boolean;
        error?: string;
    };
}

export interface FileUpload {
    name: string;
    content: string;
    type: string;
}
