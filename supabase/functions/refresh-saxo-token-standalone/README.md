# Configuration Supabase Edge Function - Refresh Token Saxo

## ⚠️ IMPORTANT : Configuration des Secrets

Avant de tester la fonction, vous **DEVEZ** configurer les secrets suivants dans Supabase :

### 1. Aller dans Settings → Edge Functions → Secrets

### 2. Ajouter ces deux secrets :

**Secret 1 : `SUPABASE_URL`**
- Valeur : `https://lowncckbivxmiakzmsxq.supabase.co`
- (Remplacez `lowncckbivxmiakzmsxq` par votre project reference ID)

**Secret 2 : `SUPABASE_SERVICE_ROLE_KEY`**
- Où le trouver : Settings → API → "service_role" (secret) → Copier la clé
- ⚠️ C'est la clé **service_role** (secret), PAS la clé anon/public !

### 3. Comment trouver votre Project Reference ID

Dans l'URL de votre dashboard Supabase :
```
https://supabase.com/dashboard/project/lowncckbivxmiakzmsxq/...
                                         ^^^^^^^^^^^^^^^^^^^
                                         C'est votre project ref
```

Votre URL Supabase sera alors : `https://lowncckbivxmiakzmsxq.supabase.co`

## Test de la fonction

### Dans l'interface Supabase

**Request Body :**
```json
{
  "account_id": 4
}
```

**Headers :**
```
Authorization: Bearer votre_clé_publishable_supabase
```

### Dans cron-job.org

**URL :** `https://lowncckbivxmiakzmsxq.supabase.co/functions/v1/refresh-saxo-token-standalone`

**Method :** POST

**Headers :**
```
Authorization: Bearer votre_clé_publishable_supabase
Content-Type: application/json
```

**Body (JSON) :**
```json
{
  "account_id": 4
}
```

**Schedule :** Toutes les 45 minutes

## Dépannage

### Erreur "SUPABASE_URL non trouvé"
→ Ajoutez le secret `SUPABASE_URL` dans Settings → Edge Functions → Secrets

### Erreur "SUPABASE_SERVICE_ROLE_KEY non trouvé"
→ Ajoutez le secret `SUPABASE_SERVICE_ROLE_KEY` (la clé service_role, pas anon !)

### Erreur "Unexpected token '<'"
→ Les secrets ne sont pas configurés ou l'URL Supabase est incorrecte

### Erreur "Compte broker Saxo non trouvé"
→ Vérifiez que le compte existe dans la table `trading_brokeraccount` avec `broker_type = 'SAXO'` et l'ID correct



