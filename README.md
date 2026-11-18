# DitStock — backend (API)

API REST de **DitStock**, application de gestion de stock pour les petits commerçants et PME sénégalais
(boutiques, quincailleries, dépôts) : catalogue de produits, fournisseurs, entrepôts, entrées et sorties
de stock, alertes de seuil, tableau de bord, rapports et journal d'audit. Prix en FCFA.

Ce dépôt fait partie d'une architecture **multi-repositories** :

| Dépôt | Rôle |
|---|---|
| **ditstock_backend** (ce dépôt) | API Flask — CI : tests, image Docker publiée sur Docker Hub |
| [ditstock_frontend](https://github.com/Mj2k-styles/ditstock_frontend) | Interface React — CI : tests, image Docker publiée sur Docker Hub |
| dépôt de déploiement | Manifests Kubernetes — CD : déploie les images publiées |

## Technologies

Python 3.12, **Flask** + Flask-RESTX (documentation Swagger/OpenAPI), SQLAlchemy + Alembic (migrations),
marshmallow (validation), JWT (Flask-JWT-Extended), **PostgreSQL 16**, Gunicorn, métriques Prometheus.

## API

La documentation interactive Swagger est servie à la racine (`http://localhost:5000`).

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health/` | État de l'API (sondes Kubernetes) |
| POST | `/api/auth/login` · `/refresh` · `/forgot-password` · `/reset-password` | Authentification |
| GET, POST | `/api/products/` | Lister (recherche, filtres, pagination) et créer des produits |
| GET, PUT, DELETE | `/api/products/{id}` | Consulter, modifier, archiver un produit |
| POST | `/api/products/import` | Import CSV |
| GET, POST | `/api/movements/` | Historique et saisie des entrées, sorties, transferts, ajustements |
| GET | `/api/alerts/` | Produits sous le seuil minimal |
| GET | `/api/dashboard/stats` · `/movements` · `/top-exits` | Indicateurs, évolution sur 30 jours, top 10 des sorties |
| GET, POST, PUT, DELETE | `/api/categories/`, `/api/suppliers/`, `/api/warehouses/`, `/api/warehouse-stocks/`, `/api/users/` | Référentiels et utilisateurs |
| GET | `/api/suppliers/{id}/movements` | Historique des approvisionnements d'un fournisseur |
| GET | `/api/exports/stock/{csv,pdf}` · `/api/exports/movements/{csv,pdf}` | Rapports CSV et PDF |
| GET | `/api/audit-logs/` | Journal d'audit (administrateur) |
| GET | `/metrics` | Métriques Prometheus |

Rôles : **magasinier** (entrées et sorties), **gestionnaire** (catalogue, transferts, ajustements, rapports),
**administrateur** (tout, dont utilisateurs, entrepôts et audit). Chaque route vérifie le rôle.

## Lancer en local

```bash
docker compose up --build
```

La base est migrée et remplie avec des données de démonstration. Comptes (mot de passe `Demo12345!`) :
`admin@ditstock.local`, `gestionnaire@ditstock.local`, `magasinier@ditstock.local`.

Sans Docker :

```bash
python -m venv venv && source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
flask db upgrade && ALLOW_DEMO_SEED=1 flask seed-demo
flask run --debug
```

## Tests

```bash
flake8                                              # style
bandit -r app -ll                                   # sécurité du code
python -m pytest --cov=app --cov-fail-under=70      # tests unitaires et d'intégration (SQLite en mémoire)
```

## Image Docker

Image multi-étapes basée sur `python:3.12-slim`, exécutée par un utilisateur non root, servie par Gunicorn
sur le port 5000, avec un `HEALTHCHECK` sur `/health/`. Au démarrage, `docker-entrypoint.sh` applique les
migrations si `RUN_MIGRATIONS=1`.

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL (obligatoire) |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Secrets de l'application (obligatoires) |
| `RUN_MIGRATIONS` | `1` : `flask db upgrade` au démarrage |
| `FRONTEND_URL` | Adresse du frontend (liens des e-mails) |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` | E-mails (mot de passe oublié, alertes) |
| `GUNICORN_WORKERS`, `LOG_FORMAT`, `LOG_LEVEL` | Exécution et journaux (JSON par défaut) |

## CI (GitHub Actions)

Le pipeline [`.github/workflows/ci.yml`](.github/workflows/ci.yml) s'exécute à chaque push et pull request :

1. **checkout** du code ;
2. **installation** des dépendances ;
3. **lint** Flake8, analyse **Bandit**, **tests unitaires** pytest (échec sous 70 % de couverture, rapport en artefact) ;
   recherche de secrets **Gitleaks** en parallèle ;
4. **build de l'image Docker** et scan **Trivy** (échec sur une vulnérabilité critique corrigeable) ;
5. **push sur Docker Hub** (branche `main` et tags `v*`) avec les tags `sha-<commit>`, `latest` et `X.Y.Z` ;
6. **déclenchement du dépôt de déploiement** (`repository_dispatch`, événement `image-publiee`) avec le tag publié.

Pourquoi **GitHub Actions** : le code est déjà sur GitHub, l'outil est intégré (aucun serveur Jenkins à
maintenir), gratuit pour ce volume, et les dépôts se déclenchent entre eux nativement (`repository_dispatch`).

Configuration (Settings → Secrets and variables → Actions) :

| Type | Nom | Valeur |
|---|---|---|
| Variable | `DOCKERHUB_USERNAME` | compte Docker Hub |
| Secret | `DOCKERHUB_TOKEN` | jeton d'accès Docker Hub (Read & Write) |
| Variable | `DEPLOYMENT_REPO` | `Mj2k-styles/<dépôt de déploiement>` |
| Secret | `DEPLOYMENT_TOKEN` | jeton GitHub (fine-grained) avec *Actions : write* sur le dépôt de déploiement |

Tant que Docker Hub n'est pas configuré, l'image est construite et scannée mais pas publiée.

## Structure

```
app/            application Flask : models/, routes/, schemas/, services/, utils/
migrations/     migrations Alembic
tests/          tests pytest
Dockerfile      image de production
docker-entrypoint.sh, gunicorn.conf.py
```
