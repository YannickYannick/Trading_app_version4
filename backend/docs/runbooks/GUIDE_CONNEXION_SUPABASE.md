# Guide de Connexion Supabase

Ce projet utilise **Supabase (PostgreSQL)** comme base de données.

## Fichier `.env`
Le fichier `.env` à la racine du dossier `backend/` est **OBLIGATOIRE** pour le fonctionnement en local.
Il **ne doit pas** être commité sur Git (il contient des secrets).

### Configuration Requise (Mode Direct)
Nous utilisons le mode **Connection Directe** (port 5432) car le mode "Transaction Pooler" (port 6543) peut causer des erreurs `Tenant or user not found` avec certaines configurations Django/IPv6.

Copiez ce contenu dans `backend/.env` :

```ini
# Configuration Django
SECRET_KEY=votre-cle-secrete-en-dev
DEBUG=True

# Base de données Supabase PostgreSQL
USE_SUPABASE=true
DB_NAME=postgres
# Utilisateur 'postgres' standard pour la connexion directe
DB_USER=postgres
# VOTRE MOT DE PASSE (défini dans le dashboard Supabase > Settings > Database)
DB_PASSWORD=votre_mot_de_passe_ici
# Hôte DIRECT (commence par 'db.', PAS 'aws-0...')
DB_HOST=db.lowncckbivxmiakzmsxq.supabase.co
# Port 5432 pour la connexion directe (nécessaire pour éviter les erreurs de pooler)
DB_PORT=5432
```

## Résolution de problèmes courants

### Erreur `fe_sendauth: no password supplied`
**Cause :** Le fichier `.env` est manquant ou la variable `DB_PASSWORD` est vide.
**Solution :** Créez le fichier `.env` et ajoutez le mot de passe.

### Erreur `FATAL: Tenant or user not found`
**Cause :** Vous essayez d'utiliser le "Transaction Pooler" (port 6543) ou l'hôte `aws-0...` avec des paramètres incorrects.
**Solution :** Passez en connexion directe :
1. Changez `DB_PORT` à `5432`.
2. Changez `DB_HOST` pour utiliser l'URL commençant par `db.`.
3. Changez `DB_USER` à `postgres`.

### Erreur `Network Error` sur Mobile
**Cause :** L'application mobile n'arrive pas à joindre le backend.
**Solution :**
1. Assurez-vous que le backend écoute sur toutes les interfaces : `python manage.py runserver 0.0.0.0:8000`.
2. Vérifiez que `mobile/src/config/constants.ts` pointe vers l'IP locale de votre PC (`192.168.1.171`).

## Lancement pour le Mobile
Pour que l'application mobile (sur votre téléphone) puisse accéder au backend sur votre PC, vous devez lancer le serveur en **écoutant sur toutes les interfaces (0.0.0.0)**.

**Commande à utiliser :**
```bash
python manage.py runserver 0.0.0.0:8000
```

Si vous lancez juste `python manage.py runserver`, le site ne sera accessible que depuis le PC (localhost), pas depuis le téléphone.

### Vérification
1. Connectez votre téléphone au même réseau WiFi que le PC.
2. Vérifiez l'IP locale de votre PC (`ipconfig` -> IPv4, ex: `192.168.1.171`).
3. Assurez-vous que `mobile/src/config/constants.ts` utilise bien cette IP :
   ```typescript
   export const API_URL = 'http://192.168.1.171:8000/api';
   ```
