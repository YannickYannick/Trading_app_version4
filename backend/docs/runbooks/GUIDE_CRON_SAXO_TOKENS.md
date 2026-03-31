# Guide : Configuration du Cron Job pour Rafraîchissement des Tokens Saxo

## 📋 Vue d'ensemble

Ce guide explique comment configurer un cron job sur HostArmada pour rafraîchir automatiquement les tokens OAuth2 des brokers Saxo toutes les 20 minutes.

---

## 🎯 Commande Django Existante

La commande `refresh_broker_tokens` est déjà implémentée dans le backend :
- **Fichier :** `apps/trading/management/commands/refresh_broker_tokens.py`
- **Fonction :** Rafraîchit les tokens OAuth2 des comptes Saxo avant leur expiration
- **Test manuel :** `python manage.py refresh_broker_tokens --help`

---

## ⚙️ Configuration via cPanel

### Étape 1 : Accéder à l'interface Cron Jobs

1. Connecte-toi à **cPanel** (https://fra2.hostarmada.net:2083)
2. Cherche **"Cron Jobs"** dans la barre de recherche
3. Ou va dans **Advanced > Cron Jobs**

### Étape 2 : Créer le Cron Job

#### Configuration

| Champ | Valeur |
|-------|--------|
| **Minute** | `*/20` (toutes les 20 minutes) |
| **Hour** | `*` (toutes les heures) |
| **Day** | `*` (tous les jours) |
| **Month** | `*` (tous les mois) |
| **Weekday** | `*` (tous les jours de la semaine) |

#### Commande (Version Optimale - Recommandée)

Copie-colle cette commande **EXACTEMENT** dans le champ "Command" :

```bash
/home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/python /home/lebaffc1/Trading_app_version4/backend/manage.py refresh_broker_tokens --minutes-before 30 >> /home/lebaffc1/logs/cron_saxo_tokens.log 2>&1
```

**Avantages de cette méthode :**
- ✅ Plus rapide (pas d'activation de shell)
- ✅ Plus fiable (pas de problème de PATH)
- ✅ Plus simple à débugger
- ✅ Recommandé pour les cron jobs

#### Commande Alternative (avec activation virtualenv)

Si la version optimale ne fonctionne pas, utilise cette alternative :

```bash
source /home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/activate && cd /home/lebaffc1/Trading_app_version4/backend && python manage.py refresh_broker_tokens --minutes-before 30 >> /home/lebaffc1/logs/cron_saxo_tokens.log 2>&1
```

### Étape 3 : Sauvegarder

1. Clique sur **"Add New Cron Job"**
2. Vérifie que le cron apparaît dans la liste des crons actifs

---

## 📊 Explication de la Commande

### Version Optimale (Recommandée)

```bash
/home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/python \
    /home/lebaffc1/Trading_app_version4/backend/manage.py \
    refresh_broker_tokens \
    --minutes-before 30 \
    >> /home/lebaffc1/logs/cron_saxo_tokens.log 2>&1
```

**Explication ligne par ligne :**

1. `/home/lebaffc1/virtualenv/.../bin/python` 
   → Utilise l'interpréteur Python du virtualenv directement (pas besoin d'activation)

2. `/home/lebaffc1/Trading_app_version4/backend/manage.py`
   → Chemin absolu vers le script manage.py de Django

3. `refresh_broker_tokens`
   → Nom de la commande Django à exécuter

4. `--minutes-before 30`
   → Rafraîchit les tokens expirant dans moins de 30 minutes
   → Avec une exécution toutes les 20 min, on garde une marge de sécurité

5. `>> /home/lebaffc1/logs/cron_saxo_tokens.log 2>&1`
   → Redirige la sortie (stdout + stderr) vers un fichier de log
   → Permet de débugger en cas de problème

### Version Alternative (avec activation)

```bash
source /home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/activate && \
cd /home/lebaffc1/Trading_app_version4/backend && \
python manage.py refresh_broker_tokens --minutes-before 30 \
    >> /home/lebaffc1/logs/cron_saxo_tokens.log 2>&1
```

Cette version active d'abord le virtualenv. Utilise-la si la version optimale échoue.

---

## 🧪 Test de la Configuration

### Test Manuel (via SSH)

```bash
# 1. Connexion SSH
ssh -p 19199 -i id_rsa_v2 lebaffc1@fra2.hostarmada.net

# 2. Activation de l'environnement
source /home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/activate

# 3. Navigation
cd /home/lebaffc1/Trading_app_version4/backend

# 4. Test de la commande
python manage.py refresh_broker_tokens --help

# 5. Exécution forcée (test)
python manage.py refresh_broker_tokens --force
```

### Vérification du Cron

```bash
# Lister les crons actifs
crontab -l

# Voir les logs du cron
tail -f /home/lebaffc1/logs/cron_saxo_tokens.log

# Voir les dernières 50 lignes
tail -n 50 /home/lebaffc1/logs/cron_saxo_tokens.log
```

---

## 📈 Monitoring

### Consulter les Logs

```bash
# Temps réel
tail -f /home/lebaffc1/logs/cron_saxo_tokens.log

# Filtrer les erreurs
grep "❌" /home/lebaffc1/logs/cron_saxo_tokens.log

# Filtrer les succès
grep "✅ Token rafraîchi" /home/lebaffc1/logs/cron_saxo_tokens.log

# Compter les rafraîchissements réussis aujourd'hui
grep "$(date +%Y-%m-%d)" /home/lebaffc1/logs/cron_saxo_tokens.log | grep "✅" | wc -l
```

### Exemple de Sortie Attendue

```
🔄 Recherche des tokens à rafraîchir (expiration < 2026-01-04 16:25:00+01:00)...
📋 2 compte(s) trouvé(s)
  🔄 Rafraîchissement du token pour Saxo Live (ID: 1)...
    ✅ Token rafraîchi (expire: 2026-01-04 16:50:00)
  🔄 Rafraîchissement du token pour Saxo Demo (ID: 2)...
    ✅ Token rafraîchi (expire: 2026-01-04 16:50:00)

📊 Résumé:
  ✅ Rafraîchis: 2
  ❌ Échecs: 0
  ⏭️  Ignorés: 0

✅ 2 token(s) rafraîchi(s) avec succès!
```

---

## 🔧 Options Avancées

### Fréquence Alternative : Toutes les 15 minutes

```bash
*/15 * * * * source /home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/activate && cd /home/lebaffc1/Trading_app_version4/backend && python manage.py refresh_broker_tokens --minutes-before 20 >> /home/lebaffc1/logs/cron_saxo_tokens.log 2>&1
```

### Refresh Forcé (toutes les 6 heures)

```bash
0 */6 * * * source /home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/activate && cd /home/lebaffc1/Trading_app_version4/backend && python manage.py refresh_broker_tokens --force >> /home/lebaffc1/logs/cron_saxo_tokens.log 2>&1
```

### Alertes Email en Cas d'Erreur

Ajoute cette ligne **AVANT** la ligne de commande dans cPanel :

```bash
MAILTO=ton-email@domain.com
```

---

## 🚨 Dépannage

### Problème : Le cron ne s'exécute pas

**Vérifications :**
1. Vérifie que le cron est bien listé : `crontab -l`
2. Vérifie les permissions : `ls -la /home/lebaffc1/Trading_app_version4/backend/manage.py`
3. Vérifie le fichier de log : `cat /home/lebaffc1/logs/cron_saxo_tokens.log`

### Problème : Erreurs dans les logs

**Erreur : `ModuleNotFoundError`**
```bash
# Réinstaller les dépendances
source /home/lebaffc1/virtualenv/Trading_app_version4/backend/3.12/bin/activate
cd /home/lebaffc1/Trading_app_version4/backend
pip install -r requirements.txt
```

**Erreur : `OperationalError: database`**
```bash
# Vérifier la connexion à Supabase
python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()
```

### Problème : Tokens expirent quand même

**Causes possibles :**
1. Le cron ne s'exécute pas assez souvent (augmenter la fréquence)
2. Le `--minutes-before` est trop faible (augmenter à 40-50)
3. Problème d'authentification Saxo (refresh_token invalide)

**Solution :**
```bash
# Forcer le refresh de tous les tokens
python manage.py refresh_broker_tokens --force
```

---

## 📝 Notes Importantes

### Durée de Vie des Tokens Saxo

- **Access Token :** ~20-30 minutes
- **Refresh Token :** ~90 jours (à renouveler via login utilisateur)
- **Recommandation :** Cron toutes les 20 min avec `--minutes-before 30`

### Sécurité

- Les tokens ne sont **jamais loggés en clair**
- Stockage sécurisé en base de données (Supabase)
- Connexion HTTPS uniquement

### Performance

- Temps d'exécution : **<5 secondes** pour 2-3 comptes
- Impact serveur : **négligeable**
- Utilisation API Saxo : **1 requête par token rafraîchi**

---

## ✅ Checklist de Validation

- [ ] Cron job créé dans cPanel
- [ ] Commande testée manuellement via SSH
- [ ] Fichier de log créé et accessible
- [ ] Premier rafraîchissement réussi (visible dans les logs)
- [ ] Tokens en base de données mis à jour (vérifier via admin Django)
- [ ] Monitoring en place (consultation des logs régulière)

---

## 📞 Support

En cas de problème persistant :
1. Consulte les logs : `/home/lebaffc1/logs/cron_saxo_tokens.log`
2. Vérifie la commande Django : `python manage.py refresh_broker_tokens --help`
3. Contacte le support HostArmada si problème serveur

---

**Date de création :** 04/01/2026  
**Version :** 1.0
