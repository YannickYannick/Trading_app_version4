# Configuration de Déploiement - HostArmada

Ce dossier contient les fichiers de configuration utilisés pour le déploiement sur HostArmada (le-baff.com).

## 📁 Structure

```
deployment_config/
├── backend/
│   └── .env.production          # Variables d'environnement backend (production)
├── frontend/
│   ├── .env.production          # Variables d'environnement frontend (production)
│   └── .htaccess                # Configuration Apache pour SPA routing
└── README.md                    # Ce fichier
```

## 🚀 Utilisation

### Backend

**Pour déployer sur HostArmada :**
```bash
# Copier le fichier .env.production vers le serveur
scp -P 19199 -i backend/id_rsa_v2 deployment_config/backend/.env.production lebaffc1@fra2.hostarmada.net:Trading_app_version4/backend/.env
```

**Note :** Le fichier `passenger_wsgi.py` existe déjà dans `backend/` et est synchronisé.

### Frontend

**Pour build et déployer :**

1. Copier `.env.production` avant le build :
```bash
cp deployment_config/frontend/.env.production frontend/.env.production
```

2. Build du frontend :
```bash
cd frontend
npm run build:fast
```

3. Copier le .htaccess dans le dossier dist :
```bash
cp deployment_config/frontend/.htaccess frontend/dist/.htaccess
```

4. Upload vers le serveur :
```bash
cd frontend/dist
scp -P 19199 -i ../../backend/id_rsa_v2 index.html .htaccess lebaffc1@fra2.hostarmada.net:public_html/
scp -r -P 19199 -i ../../backend/id_rsa_v2 assets lebaffc1@fra2.hostarmada.net:public_html/
```

## ⚠️ Sécurité

- **NE PAS** commiter ce dossier sur Git public (contient des credentials)
- Ajouter au `.gitignore` si nécessaire
- Les mots de passe doivent être changés régulièrement

## 🔄 Différences avec le Code Local

Les fichiers suivants **sont déjà synchronisés** entre local et HostArmada :
- ✅ `backend/passenger_wsgi.py`
- ✅ `backend/config_django/settings/base.py` (fonction `cast_bool`)
- ✅ `backend/config_django/settings/production.py` (WhiteNoise)
- ✅ `backend/requirements.txt` (whitenoise)
- ✅ `frontend/package.json` (script `build:fast`)
- ✅ `frontend/tsconfig.json` (strict: false)
- ✅ `frontend/src/vite-env.d.ts`

Les fichiers dans ce dossier `deployment_config/` sont les **seuls manquants** en local.

## 📚 Documentation

Pour plus d'informations sur le processus de déploiement complet, consultez :
- `RAPPORT_DEPLOIEMENT_HOSTARMADA.md` (rapport détaillé du déploiement)
- `backend/GUIDE_CRON_SAXO_TOKENS.md` (configuration des cron jobs)
- `GUIDE_MODES_ENVIRONNEMENT.md` (basculer entre dev/prod)

## 🐳 Alternative : Docker

Docker aurait pu simplifier le déploiement en encapsulant toute la configuration dans des conteneurs. 

**Avantages Docker :**
- Configuration identique dev/prod
- Déploiement reproductible
- Pas de dépendance à l'infrastructure du serveur

**Pourquoi pas utilisé ici :**
- HostArmada utilise cPanel/Passenger (hébergement mutualisé)
- Pas d'accès Docker sur hébergement partagé
- Docker nécessite un VPS/serveur dédié

**Recommandation future :**
Si vous passez à un VPS (DigitalOcean, AWS, etc.), migrer vers Docker + Docker Compose serait une excellente amélioration.
