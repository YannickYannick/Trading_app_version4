/**
 * Types TypeScript pour l'AI Assistant
 */

export interface AIAnalysis {
    id: number;
    user: number;
    analysis_type: AnalysisType;
    analysis_type_display: string;
    status: AnalysisStatus;
    status_display: string;
    scope_description: string;
    strategy: number | null;
    strategy_detail?: StrategyDetail;
    all_asset: number | null;
    prompt: string;
    response: string;
    summary: string;
    recommendations: Recommendation[];
    insights: Insights;
    risks: Risk[];
    opportunities: Opportunity[];
    confidence_score: number | null;
    metadata: Record<string, any>;
    error_message: string;
    is_daily_report: boolean;
    is_archived: boolean;
    created_at: string;
    updated_at: string;
    completed_at: string | null;
}

export interface AIAnalysisListItem {
    id: number;
    analysis_type: AnalysisType;
    analysis_type_display: string;
    status: AnalysisStatus;
    status_display: string;
    scope_description: string;
    strategy: number | null;
    strategy_name: string | null;
    asset_symbol: string | null;
    summary: string;
    confidence_score: number | null;
    is_daily_report: boolean;
    created_at: string;
    completed_at: string | null;
}

export interface AIAnalysisQuick {
    id: number;
    analysis_type: AnalysisType;
    scope_description: string;
    summary: string;
    confidence_score: number | null;
    created_at: string;
}

export interface Recommendation {
    action: string;
    priority: 'HIGH' | 'MEDIUM' | 'LOW';
    reason: string;
}

export interface Risk {
    risk: string;
    severity: 'HIGH' | 'MEDIUM' | 'LOW';
    mitigation?: string;
}

export interface Opportunity {
    opportunity: string;
    potential_impact: string;
}

export interface Insights {
    pnl_analysis?: string;
    parameter_evaluation?: string;
    diversification_analysis?: string;
    risk_assessment?: string;
    technical_analysis?: string;
    strategy_performance?: string;
}

export interface StrategyDetail {
    id: number;
    name: string;
    algorithm_type: string;
    risk_level: string;
    is_active: boolean;
}

export type AnalysisType = 'STRATEGY' | 'PORTFOLIO' | 'ASSET' | 'MARKET';

export type AnalysisStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface AnalyzeStrategyRequest {
    strategy_id: number;
    force_new?: boolean;
}

export interface AnalyzePortfolioRequest {
    force_new?: boolean;
}

export interface AnalyzeStrategyResponse {
    message?: string;
    analysis: AIAnalysis;
}
