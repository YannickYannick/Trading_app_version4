# 🔄 Refresh Token Saxo avec Supabase Edge Function

## 📋 Vue d'ensemble

Cette documentation décrit la solution implémentée pour rafraîchir automatiquement les tokens Saxo Bank via une Edge Function Supabase, qui s'exécute toutes les 45 minutes via cron-job.org.

## 🎯 Objectif

Automatiser le rafraîchissement des tokens d'accès Saxo Bank pour éviter leur expiration, sans avoir besoin que l'application Django soit toujours en cours d'exécution.

## 🏗️ Architecture

```
cron-job.org (toutes les 45 min)
    ↓
Supabase Edge Function (refresh-saxo-token-standalone)
    ↓
API Saxo Bank (refresh token)
    ↓
Mise à jour base de données Supabase
```

## 📁 Structure des fichiers

```
supabase/
└── functions/
    └── refresh-saxo-token-standalone/
        ├── index.ts          # Code de l'Edge Function
        └── README.md         # Documentation technique
```

## 🔧 Configuration

### 1. Secrets Supabase

Dans **Supabase Dashboard → Settings → Edge Functions → Secrets**, ajouter :

**Secret 1 : `SUPABASE_URL`**
- Valeur : `https://votre-project-ref.supabase.co`
- Exemple : `https://lowncckbivxmiakzmsxq.supabase.co`

**Secret 2 : `SUPABASE_SERVICE_ROLE_KEY`**
- Où le trouver : **Settings → API → service_role (secret)**
- ⚠️ Utiliser la clé **service_role**, pas la publishable !

### 2. Déploiement de la fonction

1. Aller dans **Supabase Dashboard → Edge Functions**
2. Créer une nouvelle fonction : `refresh-saxo-token-standalone`
3. Copier le code depuis `supabase/functions/refresh-saxo-token-standalone/index.ts`
4. Cliquer sur **Deploy**

## 🔄 Fonctionnement

### Processus de refresh

1. **Récupération des credentials** depuis la table `trading_brokeraccount`
   - `saxo_refresh_token`
   - `saxo_client_id`
   - `saxo_client_secret`
   - `saxo_environment` (live/sim)

2. **Appel API Saxo Bank** pour rafraîchir le token
   - URL : `https://live.logonvalidation.net/token` (ou `sim.logonvalidation.net/token`)
   - Méthode : POST
   - Body : `grant_type=refresh_token`, `refresh_token`, `client_id`, `client_secret`

3. **Mise à jour de la base de données**
   - `saxo_access_token` : nouveau token d'accès
   - `saxo_refresh_token` : nouveau refresh token (si fourni par Saxo)
   - `saxo_token_expires_at` : date d'expiration calculée

### Réponse de l'API

```json
{
  "success": true,
  "account_id": 4,
  "account_name": "Yannick Saxo",
  "environment": "live",
  "access_token": "eyJhbGciOiJFUzI1NiIs...",
  "refresh_token": "13f794af-cee3-4c19-a060-c4a4b3741e82",
  "expires_in": 1200,
  "expires_at": "2025-12-31T15:56:05.999Z",
  "token_type": "Bearer",
  "updated_in_db": true
}
```

## 📅 Configuration cron-job.org

### 1. Créer un nouveau cron job

- **URL** : `https://votre-project-ref.supabase.co/functions/v1/refresh-saxo-token-standalone`
- **Method** : POST
- **Headers** :
  - `Authorization: Bearer votre_clé_publishable_supabase`
  - `Content-Type: application/json`
- **Body (JSON)** :
  ```json
  {
    "account_id": 4
  }
  ```
- **Schedule** : Toutes les **45 minutes** (`*/45 * * * *`)

### 2. Clé publishable Supabase

Pour obtenir la clé publishable :
1. **Settings → API Keys**
2. Onglet **"Publishable and secret API keys"**
3. Copier la clé **"default"** (cliquer sur l'icône copie pour avoir la clé complète)
4. Utiliser cette clé dans le header `Authorization: Bearer ...`

## 🧪 Test

### Test depuis l'interface Supabase

1. Aller dans **Edge Functions → refresh-saxo-token-standalone → Test**
2. **Request Body** :
   ```json
   {
     "account_id": 4
   }
   ```
3. **Headers** :
   - `Authorization: Bearer votre_clé_publishable`
4. Cliquer sur **Send**

### Test depuis la ligne de commande

```bash
curl -X POST \
  -H "Authorization: Bearer votre_clé_publishable" \
  -H "Content-Type: application/json" \
  -d '{"account_id": 4}' \
  https://votre-project-ref.supabase.co/functions/v1/refresh-saxo-token-standalone
```

## 🔍 Dépannage

### Erreur 401 : Invalid JWT

**Causes possibles :**
- La clé publishable est incomplète ou incorrecte
- Les secrets `SUPABASE_URL` ou `SUPABASE_SERVICE_ROLE_KEY` ne sont pas configurés
- La fonction n'a pas été redéployée après avoir ajouté les secrets

**Solution :**
1. Vérifier que les secrets sont bien configurés
2. Redéployer la fonction après avoir ajouté les secrets
3. Vérifier que la clé publishable est complète (150+ caractères)

### Erreur 404 : Compte SAXO introuvable

**Causes possibles :**
- Le `account_id` n'existe pas
- Le compte n'a pas `broker_type = 'SAXO'`
- Les credentials Saxo sont manquants dans la base

**Solution :**
1. Vérifier que le compte existe dans `trading_brokeraccount`
2. Vérifier que `broker_type = 'SAXO'`
3. Vérifier que `saxo_refresh_token`, `saxo_client_id`, `saxo_client_secret` sont remplis

### Erreur 500 : Supabase env vars manquantes

**Causes possibles :**
- Les secrets `SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY` ne sont pas configurés

**Solution :**
1. Ajouter les secrets dans **Settings → Edge Functions → Secrets**
2. Redéployer la fonction

## 📊 Avantages de cette solution

✅ **Indépendant de votre serveur** : Fonctionne même si votre PC/serveur Django est éteint  
✅ **Sécurisé** : Les credentials sont stockés dans la base de données Supabase  
✅ **Automatique** : Exécution toutes les 45 minutes sans intervention  
✅ **Gratuit** : Utilise le plan gratuit de cron-job.org et Supabase  
✅ **Scalable** : Peut gérer plusieurs comptes Saxo  

## 🔐 Sécurité

- Les credentials Saxo sont stockés dans la base de données Supabase (chiffrés en transit et au repos)
- La clé `service_role` est utilisée uniquement dans les secrets de la fonction (jamais exposée)
- La clé `publishable` peut être utilisée publiquement (sécurité via RLS et Edge Function)

## 📝 Notes importantes

- Le refresh token Saxo doit être valide (sinon il faut se reconnecter manuellement)
- La fonction met à jour automatiquement les tokens dans la base de données
- L'intervalle de 45 minutes est recommandé (les tokens Saxo expirent généralement après 1-2 heures)
- Plusieurs comptes peuvent être configurés (changer `account_id` dans le body JSON)

## 🔗 Ressources

- [Documentation Supabase Edge Functions](https://supabase.com/docs/guides/functions)
- [Documentation cron-job.org](https://cron-job.org/en/documentation/)
- [API Saxo Bank OAuth2](https://www.developer.saxo/openapi/learn/oauth2-authorization-code-grant)

