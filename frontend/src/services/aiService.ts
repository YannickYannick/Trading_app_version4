/**
 * Service API pour l'AI Assistant
 */
import axios from 'axios';
import {
    AIAnalysis,
    AIAnalysisListItem,
    AIAnalysisQuick,
    AnalyzeStrategyRequest,
    AnalyzePortfolioRequest,
    AnalyzeStrategyResponse,
    SuggestDiversificationRequest,
    SuggestDiversificationResponse,
} from '../types/aiTypes';
import { config } from '../utils/config';

const API_URL = config.apiBaseUrl;

// Créer une instance axios avec configuration
const api = axios.create({
    baseURL: `${API_URL}/ai`,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Intercepteur pour ajouter le token JWT
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

/**
 * Service d'analyse IA
 */
class AIService {
    /**
     * Analyse une stratégie spécifique
     */
    async analyzeStrategy(data: AnalyzeStrategyRequest): Promise<AnalyzeStrategyResponse> {
        const response = await api.post<AnalyzeStrategyResponse>('/analyses/analyze-strategy/', data);
        return response.data;
    }

    /**
     * Analyse le portefeuille complet
     */
    async analyzePortfolio(data: AnalyzePortfolioRequest = {}): Promise<AnalyzeStrategyResponse> {
        const response = await api.post<AnalyzeStrategyResponse>('/analyses/analyze-portfolio/', data);
        return response.data;
    }

    /**
     * Propose 3 actions pour diversifier le portefeuille (Gemini).
     * POST /analyses/suggest-diversification/
     */
    async suggestDiversification(
        data: SuggestDiversificationRequest = { force_new: true }
    ): Promise<SuggestDiversificationResponse> {
        const response = await api.post<SuggestDiversificationResponse>(
            '/analyses/suggest-diversification/',
            data
        );
        return response.data;
    }

    /**
     * Récupère l'historique des analyses
     */
    async getAnalyses(params?: {
        analysis_type?: string;
        status?: string;
        strategy?: number;
        is_daily_report?: boolean;
        page?: number;
    }): Promise<{ results: AIAnalysisListItem[]; count: number }> {
        const response = await api.get<{ results: AIAnalysisListItem[]; count: number }>('/analyses/', { params });
        return response.data;
    }

    /**
     * Récupère une analyse par ID
     */
    async getAnalysis(id: number): Promise<AIAnalysis> {
        const response = await api.get<AIAnalysis>(`/analyses/${id}/`);
        return response.data;
    }

    /**
     * Récupère la dernière analyse pour un scope donné
     */
    async getLatestAnalysis(params: {
        analysis_type: string;
        strategy?: number;
    }): Promise<AIAnalysisQuick | null> {
        try {
            const response = await api.get<AIAnalysisQuick>('/analyses/latest/', { params });
            return response.data;
        } catch (error: any) {
            if (error.response?.status === 404) {
                return null;
            }
            throw error;
        }
    }

    /**
     * Archive une analyse
     */
    async archiveAnalysis(id: number): Promise<{ message: string }> {
        const response = await api.post<{ message: string }>(`/analyses/${id}/archive/`);
        return response.data;
    }
}

export default new AIService();
