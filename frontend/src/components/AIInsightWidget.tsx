/**
 * Widget d'insights IA - Affiche les dernières recommandations IA
 */
import React, { useState, useEffect } from 'react';
import aiService from '../services/aiService';
import { AIAnalysisQuick } from '../types/aiTypes';
import './AIInsightWidget.css';

interface AIInsightWidgetProps {
    scope: 'STRATEGY' | 'PORTFOLIO';
    strategyId?: number;
    onAnalyze?: () => void;
}

const AIInsightWidget: React.FC<AIInsightWidgetProps> = ({ scope, strategyId, onAnalyze }) => {
    const [analysis, setAnalysis] = useState<AIAnalysisQuick | null>(null);
    const [loading, setLoading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadLatestAnalysis();
    }, [scope, strategyId]);

    const loadLatestAnalysis = async () => {
        setLoading(true);
        setError(null);

        try {
            const params: any = { analysis_type: scope };
            if (strategyId) {
                params.strategy = strategyId;
            }

            const data = await aiService.getLatestAnalysis(params);
            setAnalysis(data);
        } catch (err: any) {
            console.error('Erreur lors du chargement de l\'analyse:', err);
            setError(err.response?.data?.error || 'Impossible de charger l\'analyse');
        } finally {
            setLoading(false);
        }
    };

    const handleRequestAnalysis = async () => {
        setAnalyzing(true);
        setError(null);

        try {
            if (scope === 'STRATEGY' && strategyId) {
                await aiService.analyzeStrategy({ strategy_id: strategyId });
            } else if (scope === 'PORTFOLIO') {
                await aiService.analyzePortfolio();
            }

            // Recharger l'analyse après quelques secondes
            setTimeout(() => {
                loadLatestAnalysis();
                if (onAnalyze) onAnalyze();
            }, 2000);
        } catch (err: any) {
            console.error('Erreur lors de l\'analyse:', err);
            setError(err.response?.data?.error || 'Erreur lors de l\'analyse');
        } finally {
            setAnalyzing(false);
        }
    };

    const getScoreColor = (score: number | null) => {
        if (!score) return '';
        if (score >= 80) return 'high';
        if (score >= 60) return 'medium';
        return 'low';
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 60) return `Il y a ${diffMins} min`;
        if (diffHours < 24) return `Il y a ${diffHours}h`;
        if (diffDays === 1) return 'Hier';
        return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
    };

    if (loading) {
        return (
            <div className="ai-insight-widget loading">
                <div className="widget-header">
                    <div className="widget-icon">🤖</div>
                    <h3>Analyse IA</h3>
                </div>
                <div className="loading-spinner">Chargement...</div>
            </div>
        );
    }

    return (
        <div className="ai-insight-widget">
            <div className="widget-header">
                <div className="widget-icon">🤖</div>
                <h3>Analyse IA</h3>
                {analysis && analysis.confidence_score && (
                    <span className={`confidence-badge ${getScoreColor(analysis.confidence_score)}`}>
                        {analysis.confidence_score}%
                    </span>
                )}
            </div>

            {error && (
                <div className="widget-error">
                    <span className="error-icon">⚠️</span>
                    {error}
                </div>
            )}

            {analysis ? (
                <>
                    <div className="widget-content">
                        <div className="analysis-meta">
                            <span className="scope">{analysis.scope_description}</span>
                            <span className="date">{formatDate(analysis.created_at)}</span>
                        </div>
                        <p className="analysis-summary">{analysis.summary}</p>
                    </div>

                    <div className="widget-actions">
                        <button
                            className="btn-view-details"
                            onClick={() => window.location.href = '/ai-advisor'}
                        >
                            Voir détails
                        </button>
                        <button
                            className="btn-refresh"
                            onClick={handleRequestAnalysis}
                            disabled={analyzing}
                        >
                            {analyzing ? '⏳ Analyse...' : '🔄 Nouvelle analyse'}
                        </button>
                    </div>
                </>
            ) : (
                <div className="widget-empty">
                    <p>Aucune analyse disponible</p>
                    <button
                        className="btn-analyze"
                        onClick={handleRequestAnalysis}
                        disabled={analyzing}
                    >
                        {analyzing ? '⏳ Analyse en cours...' : '🚀 Lancer l\'analyse'}
                    </button>
                </div>
            )}
        </div>
    );
};

export default AIInsightWidget;
