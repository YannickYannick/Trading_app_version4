"""
Templates de prompts pour l'analyse IA de trading.
"""

STRATEGY_ANALYSIS_PROMPT = """
Tu es un expert en trading et analyse quantitative. Analyse la stratégie de trading suivante et fournis des recommandations détaillées.

**Informations sur la stratégie :**
- Nom : {strategy_name}
- Type d'algorithme : {algorithm_type}
- Actif : {asset_symbol} ({asset_name})
- Niveau de risque : {risk_level}
- Statut : {is_active}

**Paramètres de l'algorithme :**
{parameters}

**Performance récente (30 derniers jours) :**
{performance_data}

**Positions actuelles :**
{positions_data}

**Trades récents :**
{trades_data}

**Ton analyse doit inclure :**

1. **Résumé** : Vue d'ensemble de la stratégie et de ses performances
2. **Analyse P&L** : Explique les raisons des gains/pertes récents
3. **Évaluation des paramètres** : Les paramètres de l'algorithme sont-ils optimaux ?
4. **Recommandations** : Suggestions concrètes d'amélioration (ajustement paramètres, stop-loss, take-profit, etc.)
5. **Risques identifiés** : Risques spécifiques à cette stratégie
6. **Opportunités** : Opportunités d'optimisation ou d'amélioration

Réponds en JSON structuré avec les clés suivantes :
{{
  "summary": "résumé en 2-3 phrases",
  "pnl_analysis": "explication détaillée des performances",
  "parameter_evaluation": "évaluation des paramètres",
  "recommendations": [
    {{"action": "description action", "priority": "HIGH/MEDIUM/LOW", "reason": "justification"}}
  ],
  "risks": [
    {{"risk": "description risque", "severity": "HIGH/MEDIUM/LOW", "mitigation": "comment mitiger"}}
  ],
  "opportunities": [
    {{"opportunity": "description", "potential_impact": "impact attendu"}}
  ],
  "confidence_score": 85
}}
"""

PORTFOLIO_ANALYSIS_PROMPT = """
Tu es un expert en gestion de portefeuille et trading. Analyse le portefeuille de trading suivant et fournis des recommandations stratégiques.

**Vue d'ensemble du portefeuille :**
- Nombre de stratégies actives : {num_strategies}
- Nombre de positions ouvertes : {num_positions}
- Valeur totale des positions : {total_position_value} €
- P&L total (non réalisé) : {total_pnl} €
- P&L en pourcentage : {total_pnl_percent}%

**Stratégies actives :**
{strategies_data}

**Positions ouvertes :**
{positions_data}

**Diversification :**
{diversification_data}

**Performance globale (30 derniers jours) :**
{performance_data}

**Ton analyse doit inclure :**

1. **Résumé du portefeuille** : Vue d'ensemble de la santé du portefeuille
2. **Analyse de diversification** : Le portefeuille est-il bien diversifié ? Trop concentré sur certains actifs/secteurs ?
3. **Évaluation risque/rendement** : Le profil risque est-il aligné avec les objectifs ?
4. **Recommandations stratégiques** : Suggestions pour améliorer le portefeuille global
5. **Alertes** : Positions ou stratégies nécessitant une attention immédiate
6. **Opportunités** : Nouvelles stratégies ou actifs à considérer

Réponds en JSON structuré avec les clés suivantes :
{{
  "summary": "résumé en 2-3 phrases",
  "diversification_analysis": "analyse de la diversification",
  "risk_assessment": "évaluation du risque global",
  "recommendations": [
    {{"action": "description action", "priority": "HIGH/MEDIUM/LOW", "reason": "justification"}}
  ],
  "alerts": [
    {{"alert": "description alerte", "urgency": "HIGH/MEDIUM/LOW", "action_required": "action recommandée"}}
  ],
  "opportunities": [
    {{"opportunity": "description", "potential_impact": "impact attendu"}}
  ],
  "confidence_score": 85
}}
"""

ASSET_ANALYSIS_PROMPT = """
Tu es un expert en analyse financière et trading. Analyse l'actif suivant dans le contexte du portefeuille de l'utilisateur.

**Informations sur l'actif :**
- Symbole : {asset_symbol}
- Nom : {asset_name}
- Type : {asset_type}
- Prix actuel : {current_price}
- Variation 24h : {price_change_24h}%

**Positions actuelles sur cet actif :**
{positions_data}

**Stratégies utilisant cet actif :**
{strategies_data}

**Historique de prix (30 derniers jours) :**
{price_history}

**Ton analyse doit inclure :**

1. **Résumé** : Vue d'ensemble de l'actif et de son utilisation
2. **Analyse technique** : Tendance, supports, résistances
3. **Performance des stratégies** : Comment les stratégies performent sur cet actif ?
4. **Recommandations** : Acheter plus, vendre, conserver ?
5. **Risques** : Risques spécifiques à cet actif
6. **Opportunités** : Opportunités de trading

Réponds en JSON structuré avec les clés suivantes :
{{
  "summary": "résumé en 2-3 phrases",
  "technical_analysis": "analyse technique détaillée",
  "strategy_performance": "performance des stratégies sur cet actif",
  "recommendations": [
    {{"action": "description action", "priority": "HIGH/MEDIUM/LOW", "reason": "justification"}}
  ],
  "risks": [
    {{"risk": "description risque", "severity": "HIGH/MEDIUM/LOW"}}
  ],
  "opportunities": [
    {{"opportunity": "description", "potential_impact": "impact attendu"}}
  ],
  "confidence_score": 85
}}
"""


def format_strategy_prompt(strategy_data):
    """
    Formate le prompt pour l'analyse de stratégie.
    
    Args:
        strategy_data: Dictionnaire contenant les données de la stratégie
    
    Returns:
        str: Prompt formaté
    """
    return STRATEGY_ANALYSIS_PROMPT.format(**strategy_data)


def format_portfolio_prompt(portfolio_data):
    """
    Formate le prompt pour l'analyse de portefeuille.
    
    Args:
        portfolio_data: Dictionnaire contenant les données du portefeuille
    
    Returns:
        str: Prompt formaté
    """
    return PORTFOLIO_ANALYSIS_PROMPT.format(**portfolio_data)


def format_asset_prompt(asset_data):
    """
    Formate le prompt pour l'analyse d'actif.
    
    Args:
        asset_data: Dictionnaire contenant les données de l'actif
    
    Returns:
        str: Prompt formaté
    """
    return ASSET_ANALYSIS_PROMPT.format(**asset_data)
