import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

const api = axios.create({
    baseURL: API_BASE,
    timeout: 120000, // 2 min for AI operations
});

// ============================================
// Bring-your-own-key (in-memory only)
// ============================================
// Holds the user's own OpenAI-compatible LLM key for this browser session.
// Kept in the JS heap only — never written to localStorage/sessionStorage —
// so it is gone on refresh. Sent per-request as headers; the backend uses it
// for that request and never stores it.
export const llmCredentials = { apiKey: '', model: '', baseUrl: '' };

export const setLlmCredentials = ({ apiKey = '', model = '', baseUrl = '' }) => {
    llmCredentials.apiKey = apiKey.trim();
    llmCredentials.model = model.trim();
    llmCredentials.baseUrl = baseUrl.trim();
};

export const hasLlmKey = () => Boolean(llmCredentials.apiKey);

api.interceptors.request.use((config) => {
    if (llmCredentials.apiKey) {
        config.headers['X-LLM-API-Key'] = llmCredentials.apiKey;
        if (llmCredentials.model) config.headers['X-LLM-Model'] = llmCredentials.model;
        if (llmCredentials.baseUrl) config.headers['X-LLM-Base-URL'] = llmCredentials.baseUrl;
    }
    return config;
});

// ============================================
// Documents
// ============================================

export const uploadDocument = async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: onProgress,
    });
    return data;
};

export const getDocuments = async () => {
    const { data } = await api.get('/documents');
    return data;
};

export const getDocument = async (id) => {
    const { data } = await api.get(`/documents/${id}`);
    return data;
};

export const getDocumentStatus = async (id) => {
    const { data } = await api.get(`/documents/${id}/status`);
    return data;
};

export const deleteDocument = async (id) => {
    await api.delete(`/documents/${id}`);
};

export const getDocumentText = async (id) => {
    const { data } = await api.get(`/documents/${id}/text`);
    return data;
};

// ============================================
// Insights
// ============================================

export const summarizeDocument = async (id) => {
    const { data } = await api.post(`/documents/${id}/summarize`);
    return data;
};

export const extractDocument = async (id, docType = 'general') => {
    const { data } = await api.post(`/documents/${id}/extract`, { document_type: docType });
    return data;
};

export const detectRisks = async (id) => {
    const { data } = await api.post(`/documents/${id}/risks`);
    return data;
};

export const getInsights = async (id) => {
    const { data } = await api.get(`/documents/${id}/insights`);
    return data;
};

// ============================================
// Search
// ============================================

export const semanticSearch = async (query, topK = 5, documentId = null) => {
    const { data } = await api.post('/search', {
        query,
        top_k: topK,
        document_id: documentId,
    });
    return data;
};

// ============================================
// Chat
// ============================================

export const chatWithDocument = async (id, question) => {
    const { data } = await api.post(`/documents/${id}/chat`, { question });
    return data;
};

export const getChatHistory = async (id) => {
    const { data } = await api.get(`/documents/${id}/chat/history`);
    return data;
};

// ============================================
// Compare
// ============================================

export const compareDocuments = async (documentIds, comparisonType = 'general') => {
    const { data } = await api.post('/compare', {
        document_ids: documentIds,
        comparison_type: comparisonType,
    });
    return data;
};

// ============================================
// Dashboard
// ============================================

export const getDashboardStats = async () => {
    const { data } = await api.get('/dashboard/stats');
    return data;
};

export const getRiskOverview = async () => {
    const { data } = await api.get('/dashboard/risks');
    return data;
};

export const getTimeline = async () => {
    const { data } = await api.get('/dashboard/timeline');
    return data;
};

// ============================================
// Report Generation
// ============================================

export const generateReport = async (documentId, reportType = 'comprehensive') => {
    const response = await api.post('/report/generate',
        { document_id: documentId, report_type: reportType },
        { responseType: 'blob', timeout: 120000 }
    );
    // Trigger browser download
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `DocInsights_Report_${documentId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return true;
};

// ============================================
// Multi-Document Chat
// ============================================

export const multiDocumentChat = async (documentIds, question, topK = 5) => {
    const { data } = await api.post('/chat/multi', {
        document_ids: documentIds,
        question,
        top_k: topK,
    });
    return data;
};

export default api;
