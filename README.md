# AirGuard Cameroun - Backend API

API REST pour la plateforme de surveillance et prediction de la qualite de l'air au Cameroun. Prediction multi-risques (air, chaleur, inondation) par intelligence artificielle pour 40 villes camerounaises.

## Stack technique

- **Framework** : Django 6.0 + Django REST Framework
- **Base de donnees** : PostgreSQL 16
- **Auth** : JWT (access 1h / refresh 7j)
- **ML** : 5 modeles pre-entraines (XGBoost, LightGBM, Random Forest, MLP, Ensemble)
- **Chatbot** : OpenAI GPT-3.5
- **Notifications** : Firebase Cloud Messaging
- **PDF** : ReportLab (rapports professionnels)
- **Documentation** : Swagger / ReDoc (drf-spectacular)
- **Deploiement** : Docker + CI/CD GitHub Actions

## Installation locale

```bash
# 1. Cloner le repo
git clone https://github.com/ML-Masters/AirGuard_Backend.git
cd AirGuard_Backend

# 2. Lancer PostgreSQL via Docker
docker compose up airguard-db -d

# 3. Environnement virtuel
python -m venv venv
source venv/Scripts/activate  # Windows
source venv/bin/activate      # Linux/Mac

# 4. Dependances
pip install -r requirements.txt

# 5. Configuration
cp .env.example .env  # Editer avec vos credentials

# 6. Base de donnees
python manage.py migrate
python manage.py seed_locations    # 10 regions, 40 villes
python manage.py ensure_admin      # Cree le superuser

# 7. Importer le dataset (optionnel)
python manage.py seed_data --file path/to/Dataset_complet_Meteo.xlsx

# 8. Lancer le serveur
python manage.py runserver
```

## Endpoints API

### Donnees
| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/villes/` | 40 villes avec coordonnees GPS |
| GET | `/api/v1/regions/` | 10 regions du Cameroun |
| GET | `/api/v1/meteo/` | Releves meteorologiques |
| GET | `/api/v1/air-quality/` | Donnees qualite de l'air (filtrable) |
| GET | `/api/v1/air-quality/national_kpis/` | KPIs nationaux |

### Intelligence artificielle
| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/air-quality/predict/` | Prediction multi-risques (air, chaleur, inondation) |
| POST | `/api/v1/air-quality/chat/` | Chatbot IA expert qualite de l'air |

### Alertes
| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/alerts/` | Toutes les alertes |
| GET | `/api/v1/alerts/active/` | Alertes publiees actives |
| GET | `/api/v1/alerts/brouillons/` | Brouillons ML (admin) |
| POST | `/api/v1/alerts/{id}/publier/` | Publier une alerte (admin) |
| POST | `/api/v1/alerts/{id}/ignorer/` | Ignorer une alerte (admin) |
| POST | `/api/v1/alerts/scan/` | Scanner les alertes ML (admin) |

### Rapports et import
| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/air-quality/reports/pdf/` | Rapport PDF professionnel |
| POST | `/api/v1/data/import/` | Import dataset avec progression SSE |

### Authentification
| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/login/` | Connexion JWT |
| POST | `/api/v1/token/refresh/` | Rafraichir le token |
| GET | `/api/docs/` | Documentation Swagger |
| GET | `/api/redoc/` | Documentation ReDoc |

## Modeles ML

5 modeles pre-entraines charges au demarrage :

| Modele | Cible | Algorithme | R2 |
|--------|-------|------------|-----|
| PM2.5 Proxy | Qualite de l'air | Ensemble LightGBM+XGBoost | 0.99 |
| Heat Index | Indice de chaleur | Random Forest | 0.96 |
| Deficit eau | Stress hydrique | MLP | 0.84 |
| Risque inondation | Inondation | XGBoost | 0.98 |
| Chaleur extreme | Score chaleur | LightGBM | 0.99 |

## Systeme d'alertes automatiques

1. Le modele ML analyse les donnees AQI de chaque ville
2. Si AQI > 100 : alerte **brouillon** creee automatiquement
3. L'administrateur voit les brouillons et peut :
   - **Publier** : l'alerte devient visible + notifications push
   - **Modifier et publier** : ajuster le message avant publication
   - **Ignorer** : rejeter l'alerte
4. Recommandations personnalisees :
   - **Residents** : consignes detaillees selon la gravite
   - **Visiteurs** : avertissements pour eviter la zone

## Deploiement Docker

```bash
# Production
docker compose up -d --build
docker exec airguard-backend python manage.py migrate --noinput
docker exec airguard-backend python manage.py seed_locations
docker exec airguard-backend python manage.py ensure_admin
```

## CI/CD

Chaque push sur `main` declenche automatiquement :
1. Pull du code sur le VPS
2. Rebuild du container Docker
3. Migration de la base
4. Seed des villes
5. Creation du superuser

## Production

- **API** : https://api.airguard-cm.duckdns.org
- **Swagger** : https://api.airguard-cm.duckdns.org/api/docs/
- **Dashboard** : https://airguard-cm.duckdns.org

## Equipe

Projet developpe par **ML Masters** dans le cadre du Hackathon IndabaX Cameroon 2026.
