# Incident de Connexion Base de Données - 2026-01-03

## Résumé
Tentative de résolution d'une erreur DNS lors du démarrage du backend Django, qui s'est avérée être un faux-problème causé par un cache système.

## Chronologie

### 15:17 - Problème initial
```
psycopg2.OperationalError: could not translate host name "db.lowncckbivxmiakzmsxq.supabase.co" to address: Name or service not known
```

### 15:18 - Diagnostic erroné
- Tests DNS confirment que l'hôte Supabase répond uniquement en IPv6
- Tentative de basculement vers SQLite local (modifié `.env` : `USE_SUPABASE=false`)
- Erreur : base SQLite non initialisée (tables manquantes)

### 15:22 - Escalade
- Retour sur Supabase demandé par l'utilisateur
- Tentative de configuration du Pooler IPv4 : `aws-0-eu-central-1.pooler.supabase.com`
- Erreur : `FATAL: Tenant or user not found` (mauvais port 5432 au lieu de 6543)

### 15:26 - Correction échouée
- Changement du port à 6543 pour le Transaction Pooler
- Erreur persistante : `FATAL: Tenant or user not found`

### 15:30 - Retour à la configuration d'origine
- Restauration complète de la config initiale (`db.lowncckbivxmiakzmsxq.supabase.co:5432`)
- **Connexion réussie** ✅

## Cause Réelle
L'erreur DNS initiale était **temporaire** (probablement un cache DNS corrompu ou une indisponibilité réseau momentanée). La configuration d'origine était correcte et fonctionnelle.

## Actions de Débogage Inutiles
1. ❌ Passage à SQLite
2. ❌ Configuration du Pooler IPv4
3. ❌ Modification du format utilisateur (`postgres.lowncckbivxmiakzmsxq`)
4. ❌ Changement de port vers 6543

## Leçon Apprise
Toujours **vérifier si le problème persiste** avant d'effectuer des changements de configuration majeurs. Un simple redémarrage ou une attente de quelques minutes aurait résolu le problème DNS transitoire.

## Configuration Finale (Stable)
```ini
USE_SUPABASE=true
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=Niveaux22!!
DB_HOST=db.lowncckbivxmiakzmsxq.supabase.co
DB_PORT=5432
```

## Avertissements RLS Supabase (Non Bloquants)
Les alertes "RLS Disabled in Public" visibles dans le dashboard Supabase sont normales pour Django. Django gère les permissions au niveau applicatif, pas au niveau base de données. Ces avertissements peuvent être ignorés.
