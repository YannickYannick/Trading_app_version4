import React, { useState } from 'react'
import { useStrategyExecutions } from '../../hooks/useStrategyExecutions'
import { StrategyExecution } from '../../services/strategyExecutionService'
import './StrategyExecutionMonitor.css'

export default function StrategyExecutionMonitor() {
    const { executions, loading, error, executeAll } = useStrategyExecutions()
    const [executing, setExecuting] = useState(false)
    const [expandedIds, setExpandedIds] = useState<number[]>([])

    const toggleExpand = (id: number) => {
        setExpandedIds(prev =>
            prev.includes(id) ? prev.filter(eid => eid !== id) : [...prev, id]
        )
    }

    const handleExecuteAll = async () => {
        if (!window.confirm('Exécuter toutes les stratégies actives ?')) {
            return
        }

        setExecuting(true)
        try {
            const result = await executeAll()
            alert(`${result.total_strategies} stratégies exécutées`)
        } catch (err: any) {
            alert(`Erreur: ${err.message}`)
        } finally {
            setExecuting(false)
        }
    }

    const getStatusBadge = (status: string) => {
        const badges = {
            running: { label: 'En cours', className: 'badge-running' },
            completed: { label: 'Terminé', className: 'badge-completed' },
            failed: { label: 'Échoué', className: 'badge-failed' },
        }
        const badge = badges[status as keyof typeof badges] || { label: status, className: '' }
        return <span className={`status-badge ${badge.className}`}>{badge.label}</span>
    }

    const getSignalBadge = (signal: string) => {
        const badges = {
            BUY: { label: 'ACHAT', className: 'signal-buy' },
            SELL: { label: 'VENTE', className: 'signal-sell' },
            HOLD: { label: 'CONSERVER', className: 'signal-hold' },
            SKIP: { label: 'SKIP', className: 'signal-hold' },
            NONE: { label: 'Aucun', className: 'signal-none' },
        }
        const badge = badges[signal as keyof typeof badges] || { label: signal, className: '' }
        return <span className={`signal-badge ${badge.className}`}>{badge.label}</span>
    }

    const formatOutput = (execution: StrategyExecution) => {
        if (execution.error) {
            return <span className="text-danger">{execution.error}</span>
        }

        if (execution.signal_price) {
            const price = Number(execution.signal_price)
            const qty = execution.signal_quantity || 0
            return (
                <span className={qty > 0 ? "text-success" : "text-muted"}>
                    Prix: {isNaN(price) ? 'N/A' : price.toFixed(2)} € | Qté: {qty}
                </span>
            )
        }

        return <span className="text-muted">Aucune action</span>
    }

    const renderDetails = (execution: StrategyExecution) => {
        if (!execution.output) return null

        try {
            // Handle case where output is already parsed or is a string
            let output = execution.output
            if (typeof output === 'string') {
                try {
                    // Fix Python JSON specific items that are invalid in JS JSON
                    // Replace Infinity, -Infinity, NaN with strings
                    const sanitizedOutput = output
                        .replace(/:\s*Infinity/g, ': "Infinity"')
                        .replace(/:\s*-Infinity/g, ': "-Infinity"')
                        .replace(/:\s*NaN/g, ': "NaN"')

                    output = JSON.parse(sanitizedOutput)
                } catch (e) {
                    // Si ce n'est toujours pas du JSON valide, on log l'erreur mais on essaie d'afficher brute
                    console.error("JSON parse error:", e)
                }
            }

            // Vérification de sécurité
            if (!output || typeof output !== 'object') {
                return <div className="p-2 text-warning small">Format de sortie invalide</div>
            }

            const debugInfo = output.signals?.debug_info

            if (!debugInfo) return <div className="p-2 text-muted">Pas de détails disponibles (No debug_info)</div>

            const inputs = debugInfo.inputs
            if (!inputs) return <div className="p-2 text-muted">Pas de détails disponibles (No inputs)</div>

            const logic = debugInfo.logic || []
            const portfolio = inputs.portfolio || {}
            const executionExecuted = output.execution_executed || false

            return (
                <div className="execution-details mt-2 p-3 bg-dark rounded border border-secondary text-light">
                    <div className="row">
                        <div className="col-md-4">
                            <h6 className="text-info">📥 Paramètres & Portfolio</h6>
                            <table className="table table-sm table-dark table-borderless small mb-0">
                                <tbody>
                                    <tr><td className="text-muted">Prix Actuel:</td><td>{inputs.current_price} €</td></tr>
                                    <tr><td className="text-muted">Seuils (Bas/Haut):</td><td>{inputs.threshold_low} / {inputs.threshold_high} €</td></tr>
                                    <tr><td className="text-muted">Cash Dispo:</td><td>{portfolio.available_cash} €</td></tr>
                                    <tr><td className="text-muted">Qté Dispo:</td><td>{portfolio.available_qty}</td></tr>
                                    <tr><td className="text-muted">Qté Min/Max:</td><td>{inputs.min_qty} / {inputs.max_qty}</td></tr>
                                </tbody>
                            </table>
                        </div>
                        <div className="col-md-4">
                            <h6 className="text-warning">⚙️ Logique de Décision</h6>
                            <ul className="list-group list-group-flush small">
                                {logic.map((step: string, idx: number) => (
                                    <li key={idx} className="list-group-item bg-transparent py-1 px-0 border-secondary">
                                        {step.startsWith('❌') ? <span className="text-danger">{step}</span> :
                                            step.startsWith('✅') ? <span className="text-success fw-bold">{step}</span> :
                                                step.startsWith('⚠️') ? <span className="text-warning">{step}</span> :
                                                    <span className="text-secondary">{step}</span>}
                                    </li>
                                ))}
                            </ul>
                        </div>
                        {(execution.signal === 'BUY' || execution.signal === 'SELL') && execution.signal_quantity > 0 && (
                            <div className="col-md-4">
                                <h6 className={executionExecuted ? "text-success" : "text-warning"}>
                                    {executionExecuted ? '✅ Exécution Réalisée' : '⚠️ Signal Généré'}
                                </h6>
                                <table className="table table-sm table-dark table-borderless small mb-0">
                                    <tbody>
                                        <tr><td className="text-muted">Fonction:</td><td className="text-info">_execute_signal()</td></tr>
                                        <tr><td className="text-muted">Signal:</td><td className="fw-bold">{execution.signal}</td></tr>
                                        <tr><td className="text-muted">Prix Exécution:</td><td>{execution.signal_price} €</td></tr>
                                        <tr><td className="text-muted">Quantité:</td><td className="text-success">{execution.signal_quantity}</td></tr>
                                        <tr><td className="text-muted">Broker:</td><td>{output.portfolio?.broker_name || 'Simulation'}</td></tr>
                                        <tr><td className="text-muted">Coût Total:</td><td>{(Number(execution.signal_price) * Number(execution.signal_quantity)).toFixed(2)} €</td></tr>
                                        <tr>
                                            <td className="text-muted">URL API:</td>
                                            <td className="text-break small" style={{ fontSize: '0.7rem' }}>
                                                {(() => {
                                                    const brokerName = (output.portfolio?.broker_name || 'Simulation').toLowerCase();
                                                    if (brokerName.includes('binance')) {
                                                        return 'POST https://api.binance.com/api/v3/order';
                                                    } else if (brokerName.includes('saxo')) {
                                                        return 'POST https://gateway.saxobank.com/openapi/trade/v2/orders';
                                                    } else {
                                                        return 'MODE SIMULATION (pas d\'appel API)';
                                                    }
                                                })()}
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                                {executionExecuted ? (
                                    <div className="alert alert-success mt-2 mb-0 py-1 px-2 small">
                                        <strong>📊 Ordre créé en base de données</strong><br />
                                        Type: MARKET | Status: FILLED
                                        {output.quantity_was_adjusted && (
                                            <div className="mt-1 text-warning">
                                                ⚙️ Quantité ajustée: {output.quantity_original?.toFixed(8)} → {output.quantity_adjusted?.toFixed(8)}
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="alert alert-warning mt-2 mb-0 py-1 px-2 small">
                                        <strong>⚠️ Exécution automatique désactivée</strong><br />
                                        Activez "is_automated" sur la stratégie
                                    </div>
                                )}

                                {/* Afficher la réponse de l'API broker si disponible */}
                                {output.broker_api_response && (
                                    <div className={`mt-2 p-2 small border rounded ${output.broker_api_response.success ? 'border-success bg-dark' : 'border-danger bg-dark'}`}>
                                        <div className="fw-bold mb-1">
                                            {output.broker_api_response.success ? '✅ Réponse API Broker (SUCCÈS)' : '❌ Réponse API Broker (ÉCHEC)'}
                                        </div>
                                        {output.broker_api_response.success ? (
                                            <div style={{ fontSize: '0.75rem' }}>
                                                <div className="text-success">Order ID: {output.broker_api_response.order_id || 'N/A'}</div>
                                                <div className="text-muted">{output.broker_api_response.message || 'Ordre placé avec succès'}</div>
                                                {output.broker_api_response.raw_data && (
                                                    <details className="mt-1">
                                                        <summary className="text-info" style={{ cursor: 'pointer' }}>Voir détails API →</summary>
                                                        <pre className="text-light mb-0 mt-1" style={{ fontSize: '0.7rem', maxHeight: '150px', overflow: 'auto' }}>
                                                            {JSON.stringify(output.broker_api_response.raw_data, null, 2)}
                                                        </pre>
                                                    </details>
                                                )}
                                            </div>
                                        ) : (
                                            <div style={{ fontSize: '0.75rem' }}>
                                                <div className="text-danger">Erreur: {output.broker_api_response.error || output.broker_api_error || 'Erreur inconnue'}</div>
                                                {output.broker_api_response.exception_type && (
                                                    <div className="text-warning">Type: {output.broker_api_response.exception_type}</div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )
        } catch (e: any) {
            console.error("Render details error:", e)
            return <div className="text-danger small">Erreur lecture détails: {e.message}</div>
        }
    }

    return (
        <div className="strategy-execution-monitor">
            <div className="monitor-header">
                <h3>Monitoring des Stratégies</h3>
                <button
                    className="btn btn-primary"
                    onClick={handleExecuteAll}
                    disabled={executing}
                >
                    {executing ? 'Exécution...' : '▶ Exécuter toutes les stratégies'}
                </button>
            </div>

            {error && (
                <div className="alert alert-danger">{error}</div>
            )}

            <div className="monitor-table-container">
                <table className="monitor-table">
                    <thead>
                        <tr>
                            <th>Stratégie</th>
                            <th>Action</th>
                            <th>Output</th>
                            <th>Détails</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && executions.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="text-center">Chargement...</td>
                            </tr>
                        ) : executions.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="text-center text-muted">
                                    Aucune exécution récente
                                </td>
                            </tr>
                        ) : (
                            executions.map((execution) => (
                                <React.Fragment key={execution.id}>
                                    <tr
                                        onClick={() => toggleExpand(execution.id)}
                                        style={{ cursor: 'pointer' }}
                                        className={expandedIds.includes(execution.id) ? 'active-row' : ''}
                                    >
                                        <td>
                                            <div className="strategy-cell">
                                                <strong>{execution.strategy_name}</strong>
                                                <div className="strategy-meta">
                                                    {getStatusBadge(execution.status)}
                                                    <span className="text-muted small">
                                                        {new Date(execution.started_at).toLocaleTimeString('fr-FR')}
                                                    </span>
                                                    {execution.duration && (
                                                        <span className="text-muted small">
                                                            ({execution.duration}s)
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <div className="action-cell">
                                                {getSignalBadge(execution.signal)}
                                            </div>
                                        </td>
                                        <td>
                                            <div className="output-cell">
                                                {formatOutput(execution)}
                                            </div>
                                        </td>
                                        <td>
                                            <button className="btn btn-sm btn-link text-decoration-none">
                                                {expandedIds.includes(execution.id) ? '🔽' : '▶️'}
                                            </button>
                                        </td>
                                    </tr>
                                    {expandedIds.includes(execution.id) && (
                                        <tr>
                                            <td colSpan={4} className="p-0 border-0">
                                                {renderDetails(execution)}
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <div className="monitor-footer">
                <span className="text-muted small">
                    {executions.length} exécutions récentes
                </span>
            </div>
        </div>
    )
}
