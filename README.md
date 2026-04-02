# AirGuard Backend API

API REST pour la plateforme de surveillance de la qualite de l'air au Cameroun.

## Stack technique

- Django 6.0 + Django REST Framework
- PostgreSQL 16 (Docker)
- 5 modeles ML (XGBoost, LightGBM, Random Forest, MLP)
- Firebase Cloud Messaging (notifications push)
- OpenAI GPT-3.5 (chatbot IA)
- JWT (SimpleJWT) authentification
- Docker Compose + CI/CD GitHub Actions

## Endpoints API

### Authentification
| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/login/` | Connexion (email/mdp) → JWT tokens |
| POST | `/api/v1/token/refresh/` | Rafraichir le token |
| POST | `/api/v1/auth/google/` | Connexion Google Sign-In |
| POST | `/api/v1/register/` | Inscription nouvel utilisateur |

### Donnees
| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/villes/` | Liste des 40 villes |
| GET | `/api/v1/regions/` | Liste des 10 regions |
| GET | `/api/v1/air-quality/` | Donnees qualite air |
| GET | `/api/v1/meteo/` | Donnees meteorologiques |
| GET | `/api/v1/air-quality/national_kpis/` | KPIs nationaux |
| POST | `/api/v1/air-quality/predict/` | Predictions ML multi-risques |
| POST | `/api/v1/air-quality/chat/` | Chatbot IA |
| GET | `/api/v1/air-quality/reports/pdf/` | Rapport PDF |

### Alertes
| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/alerts/` | Liste alertes (paginee) |
| GET | `/api/v1/alerts/active/` | Alertes actives |
| GET | `/api/v1/alerts/brouillons/` | Brouillons ML (admin) |
| POST | `/api/v1/alerts/{id}/publier/` | Publier une alerte |
| POST | `/api/v1/alerts/{id}/ignorer/` | Ignorer une alerte |
| POST | `/api/v1/alerts/scan/` | Scanner les alertes ML |

### Utilisateurs
| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/users/` | Liste utilisateurs |
| POST | `/api/v1/users/register-fcm-token/` | Enregistrer token FCM |

### Import & Documentation
| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/data/import/` | Import dataset (SSE) |
| GET | `/api/docs/` | Swagger UI |
| GET | `/api/redoc/` | ReDoc |

## Modeles ML

| Modele | Cible | Algorithme | R2 |
|--------|-------|-----------|-----|
| PM2.5 Proxy | Qualite air | Ensemble LightGBM+XGBoost | 0.99 |
| Heat Index | Chaleur | Random Forest | 0.96 |
| Water Stress | Secheresse | MLP | 0.84 |
| Flood Risk | Inondation | XGBoost | 0.98 |
| Extreme Heat | Chaleur extreme | LightGBM | 0.99 |

## Installation locale

**Prerequis :** Python 3.12+, Docker

```bash
git clone https://github.com/ML-Masters/AirGuard_Backend.git
cd AirGuard_Backend
pip install -r requirements.txt
docker compose up -d  # PostgreSQL
python manage.py migrate
python manage.py seed_locations
python manage.py ensure_admin
python manage.py runserver
```

## Deploiement

- CI/CD GitHub Actions sur push main
- Docker Compose (PostgreSQL 16 + Gunicorn)
- VPS avec SSL (DuckDNS)

## URLs production

- API : https://api.airguard-cm.duckdns.org
- Swagger : https://api.airguard-cm.duckdns.org/api/docs/

## Equipe

ML Masters — Hackathon IndabaX Cameroun 2026
