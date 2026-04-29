/**
 * Page AI Advisor - Interface principale de consultation des analyses IA
 */
import React, { useState, useEffect } from 'react';
import aiService from '../services/aiService';
import { AIAnalysisListItem, AIAnalysis } from '../types/aiTypes';
import './AIAdvisor.css';

const AIAdvisor: React.FC = () => {
    const [analyses, setAnalyses] = useState<AIAnalysisListItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [selectedAnalysis, setSelectedAnalysis] = useState<AIAnalysis | null>(null);
    const [filterType, setFilterType] = useState<string>('ALL');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadAnalyses();
    }, [filterType]);

    const loadAnalyses = async () => {
        setLoading(true);
        setError(null);

        try {
            const params: any = {};
            if (filterType !== 'ALL') {
                params.analysis_type = filterType;
            }

            const data = await aiService.getAnalyses(params);
            setAnalyses(data.results);
        } catch (err: any) {
            console.error('Erreur lors du chargement des analyses:', err);
            setError('Impossible de charger les analyses');
        } finally {
            setLoading(false);
        }
    };

    const handleAnalyzePortfolio = async () => {
        setAnalyzing(true);
        setError(null);

        try {
            await aiService.analyzePortfolio({ force_new: true });
            setTimeout(() => {
                loadAnalyses();
                setAnalyzing(false);
            }, 3000);
        } catch (err: any) {
            console.error('Erreur lors de l\'analyse:', err);
            setError(err.response?.data?.error || 'Erreur lors de l\'analyse');
            setAnalyzing(false);
        }
    };

    const handleViewDetails = async (analysisId: number) => {
        try {
            const analysis = await aiService.getAnalysis(analysisId);
            setSelectedAnalysis(analysis);
        } catch (err) {
            console.error('Erreur lors du chargement des détails:', err);
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString('fr-FR', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, { label: string; className: string }> = {
            PENDING: { label: 'En attente', className: 'pending' },
            PROCESSING: { label: 'En cours', className: 'processing' },
            COMPLETED: { label: 'Terminée', className: 'completed' },
            FAILED: { label: 'Échec', className: 'failed' },
        };

        const statusInfo = statusMap[status] || { label: status, className: '' };
        return <span className={`status-badge ${statusInfo.className}`}>{statusInfo.label}</span>;
    };

    const getPriorityIcon = (priority: string) => {
        if (priority === 'HIGH') return '🔴';
        if (priority === 'MEDIUM') return '🟡';
        return '🟢';
    };

    return (
        <div className="ai-advisor-page">
            <div className="page-header">
                <div className="header-content">
                    <h1>🤖 Conseiller IA</h1>
                    <p>Analyses et recommandations intelligentes pour vos stratégies de trading</p>
                </div>
                <button
                    className="btn-analyze-portfolio"
                    onClick={handleAnalyzePortfolio}
                    disabled={analyzing}
                >
                    {analyzing ? '⏳ Analyse en cours...' : '🚀 Analyser le portefeuille'}
                </button>
            </div>

            {error && (
                <div className="error-banner">
                    <span className="error-icon">⚠️</span>
                    {error}
                    <button onClick={() => setError(null)}>✕</button>
                </div>
            )}

            <div className="filters-section">
                <div className="filter-tabs">
                    {['ALL', 'PORTFOLIO', 'STRATEGY'].map((type) => (
                        <button
                            key={type}
                            className={`filter-tab ${filterType === type ? 'active' : ''}`}
                            onClick={() => setFilterType(type)}
                        >
                            {type === 'ALL' ? 'Toutes' : type === 'PORTFOLIO' ? 'Portefeuille' : 'Stratégies'}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="loading-container">
                    <div className="loading-spinner-large">Chargement des analyses...</div>
                </div>
            ) : (
                <div className="analyses-grid">
                    {analyses.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-icon">📊</div>
                            <h3>Aucune analyse disponible</h3>
                            <p>Lancez votre première analyse en cliquant sur le bouton ci-dessus!</p>
                        </div>
                    ) : (
                        analyses.map((analysis) => (
                            <div
                                key={analysis.id}
                                className="analysis-card"
                                onClick={() => handleViewDetails(analysis.id)}
                            >
                                <div className="card-header">
                                    <div className="card-meta">
                                        <span className="card-type">{analysis.analysis_type_display}</span>
                                        {getStatusBadge(analysis.status)}
                                    </div>
                                    {analysis.confidence_score && (
                                        <span className="confidence-score">
                                            {analysis.confidence_score}%
                                        </span>
                                    )}
                                </div>

                                <h3 className="card-title">{analysis.scope_description}</h3>
                                <p className="card-summary">{analysis.summary}</p>
                                {analysis.status === 'FAILED' && analysis.error_message && (
                                    <p className="card-error">
                                        <strong>Détails :</strong> {analysis.error_message}
                                    </p>
                                )}

                                <div className="card-footer">
                                    <span className="card-date">{formatDate(analysis.created_at)}</span>
                                    {analysis.is_daily_report && (
                                        <span className="daily-badge">📅 Quotidien</span>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* Modal de détails */}
            {selectedAnalysis && (
                <div className="modal-overlay" onClick={() => setSelectedAnalysis(null)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>{selectedAnalysis.scope_description}</h2>
                            <button className="close-btn" onClick={() => setSelectedAnalysis(null)}>
                                ✕
                            </button>
                        </div>

                        <div className="modal-body">
                            {/* Erreur */}
                            {selectedAnalysis.status === 'FAILED' && selectedAnalysis.error_message && (
                                <section className="detail-section error-section">
                                    <h3>❌ Détails de l'échec</h3>
                                    <pre className="error-details">{selectedAnalysis.error_message}</pre>
                                </section>
                            )}
                            {/* Résumé */}
                            <section className="detail-section">
                                <h3>📋 Résumé</h3>
                                <p>{selectedAnalysis.summary}</p>
                            </section>

                            {/* Recommandations */}
                            {selectedAnalysis.recommendations.length > 0 && (
                                <section className="detail-section">
                                    <h3>💡 Recommandations</h3>
                                    <div className="recommendations-list">
                                        {selectedAnalysis.recommendations.map((rec, idx) => (
                                            <div key={idx} className="recommendation-item">
                                                <div className="rec-header">
                                                    <span className="rec-icon">{getPriorityIcon(rec.priority)}</span>
                                                    <span className="rec-priority">{rec.priority}</span>
                                                </div>
                                                <p className="rec-action">{rec.action}</p>
                                                <p className="rec-reason">{rec.reason}</p>
                                            </div>
                                        ))}
                                    </div>
                                </section>
                            )}

                            {/* Risques */}
                            {selectedAnalysis.risks.length > 0 && (
                                <section className="detail-section">
                                    <h3>⚠️ Risques identifiés</h3>
                                    <div className="risks-list">
                                        {selectedAnalysis.risks.map((risk, idx) => (
                                            <div key={idx} className="risk-item">
                                                <div className="risk-header">
                                                    <span className="risk-severity">{risk.severity}</span>
                                                </div>
                                                <p className="risk-description">{risk.risk}</p>
                                                {risk.mitigation && (
                                                    <p className="risk-mitigation">
                                                        <strong>Mitigation :</strong> {risk.mitigation}
                                                    </p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </section>
                            )}

                            {/* Opportunités */}
                            {selectedAnalysis.opportunities.length > 0 && (
                                <section className="detail-section">
                                    <h3>🎯 Opportunités</h3>
                                    <div className="opportunities-list">
                                        {selectedAnalysis.opportunities.map((opp, idx) => (
                                            <div key={idx} className="opportunity-item">
                                                <p className="opp-description">{opp.opportunity}</p>
                                                <p className="opp-impact">Impact : {opp.potential_impact}</p>
                                            </div>
                                        ))}
                                    </div>
                                </section>
                            )}

                            {/* Insights */}
                            {Object.values(selectedAnalysis.insights).some((v) => v) && (
                                <section className="detail-section">
                                    <h3>📊 Insights détaillés</h3>
                                    <div className="insights-content">
                                        {Object.entries(selectedAnalysis.insights).map(([key, value]) =>
                                            value ? (
                                                <div key={key} className="insight-item">
                                                    <h4>{key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}</h4>
                                                    <p>{value}</p>
                                                </div>
                                            ) : null
                                        )}
                                    </div>
                                </section>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AIAdvisor;
