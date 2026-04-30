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

DIVERSIFY_PROMPT = """
Tu es un expert en allocation d'actifs, analyse fondamentale et macroéconomie.
L'utilisateur souhaite **diversifier son portefeuille** en passant d'éventuels nouveaux ordres sur des actions.

**Contexte portefeuille (positions ouvertes) :**
- Nombre de positions : {num_positions}
- Valeur totale estimée des positions : {total_position_value} (devise de référence : {dominant_currency})
- Exposition actuelle par ligne (symbole, nom, secteur, industrie, poids approximatif du portefeuille) :
{positions_detailed}

**Secteurs et industries déjà présents (à éviter de dupliquer pour les 3 suggestions) :**
{sectors_and_industries_held}

**Mission :**
Propose **exactement 3 actions** (titres cotés) qui **complètent** le portefeuille : secteurs/industries **différents** de ceux déjà fortement représentés, géographies ou styles variés si pertinent.

Pour **chaque** suggestion, fournis :
- Identifiants : symbole court (ex: NVDA), **yahoo_symbol** (format Yahoo Finance, ex: NVDA, MC.PA, VUSA.L)
- **name** : nom de l'entreprise ou du fonds
- **sector**, **industry**, **country**
- **fundamentals** : objet avec au minimum **per** (nombre ou null si inconnu), **valuation** (texte court : valorisation boursière, multiples, etc.), **profitability** (texte court : marges, ROE, cash-flows, etc.)
- **moat** : avantages compétitifs et barrières à l'entrée (texte structuré)
- **company_strategy** : stratégie de l'entreprise (produits, R&D, M&A, distribution, etc.)
- **diversification_reason** : pourquoi cette ligne améliore la diversification **par rapport au portefeuille décrit**
- **macro_and_geopolitical** : contexte économique et politique pertinent (banques centrales Fed/BCE, politique budgétaire, tensions géopolitiques, guerres commerciales, etc.) **sans** injonction d'achat/vente
- **investment_horizon** : recommandation d'horizon (court terme < 1 an, moyen terme 1-3 ans, long terme 3+ ans) avec justification en une phrase
- **risks** : liste de 2 à 4 chaînes (risques spécifiques au titre ou au secteur)
- **confidence** : score 0-100 (qualité de ton argumentaire, pas une garantie de performance)

**Niveau global :**
- **macro_context** : synthèse macro (2-4 phrases) : cycle, taux, inflation, géopolitique, facteurs Trump ou équivalents si pertinents
- **summary** : synthèse en 2-3 phrases de la logique des 3 choix

**Règles :**
- Réponds **uniquement** en JSON valide UTF-8, sans markdown ni texte hors JSON.
- Les 3 suggestions doivent être **distinctes** (pas le même yahoo_symbol).
- Ne pas inventer de chiffres précis : si incertain, mets **null** pour per et explique dans les textes.
- Rappel légal : formulations de type « à titre informatif », pas de conseil personnalisé réglementé ; l'utilisateur reste responsable de ses décisions.

Schéma JSON exact :
{{
  "summary": "...",
  "macro_context": "...",
  "suggestions": [
    {{
      "symbol": "NVDA",
      "yahoo_symbol": "NVDA",
      "name": "NVIDIA Corporation",
      "sector": "...",
      "industry": "...",
      "country": "...",
      "fundamentals": {{ "per": null, "valuation": "...", "profitability": "..." }},
      "moat": "...",
      "company_strategy": "...",
      "diversification_reason": "...",
      "macro_and_geopolitical": "...",
      "investment_horizon": "moyen terme (1-3 ans) — ...",
      "risks": ["...", "..."],
      "confidence": 72
    }}
  ]
}}
"""


def format_diversify_prompt(diversify_data):
    """
    Formate le prompt pour les suggestions de diversification (3 actions).

    Args:
        diversify_data: dict avec positions_detailed, sectors_and_industries_held,
            total_position_value, dominant_currency, num_positions

    Returns:
        str: Prompt formaté
    """
    return DIVERSIFY_PROMPT.format(**diversify_data)


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
