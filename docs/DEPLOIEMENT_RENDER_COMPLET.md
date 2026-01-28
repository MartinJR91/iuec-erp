# Guide Complet de Déploiement IUEC-ERP sur Render

**Date de création** : 27 janvier 2026  
**Version** : 1.0  
**Auteur** : Documentation technique IUEC-ERP

---

## Table des matières

1. [Architecture du projet](#architecture-du-projet)
2. [Configuration Backend Django](#configuration-backend-django)
3. [Configuration Frontend React](#configuration-frontend-react)
4. [Déploiement Render - Backend](#déploiement-render---backend)
5. [Déploiement Render - Keycloak](#déploiement-render---keycloak)
6. [Logs de déploiement](#logs-de-déploiement)
7. [Commandes Git](#commandes-git)
8. [Troubleshooting](#troubleshooting)
9. [Checklist de déploiement](#checklist-de-déploiement)

---

## Architecture du projet

### Stack technique

- **Backend** : Django 5.1.5 (Python 3.12)
- **Frontend** : React 18.3.1 (TypeScript strict)
- **Base de données** : PostgreSQL 16 (Render free tier)
- **Authentification** : Keycloak 26.5.2 (OIDC/JWT)
- **Serveur WSGI** : Gunicorn 22.0.0
- **Static files** : WhiteNoise 6.7.0
- **Conteneurisation** : Docker (multi-stage build)

### Structure monorepo

```
iuec-erp/
├── backend/              # Django backend
│   ├── apps/             # Modules métiers
│   │   ├── academic/     # Gestion académique
│   │   ├── finance/      # Gestion financière
│   │   ├── identity/     # Identités utilisateurs
│   │   ├── rbac/         # Rôles et permissions
│   │   └── rh/           # Ressources humaines
│   ├── core/             # Configuration Django
│   ├── api/              # API REST (DRF)
│   ├── templates/        # Templates HTML (SPA React)
│   ├── static/           # Assets statiques (générés)
│   ├── Dockerfile        # Build Docker multi-stage
│   └── entrypoint.sh     # Script de démarrage
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # Composants React
│   │   ├── context/      # Contextes (Auth, Role)
│   │   ├── pages/        # Pages de l'application
│   │   └── services/     # Services API
│   └── package.json
├── render.yaml           # Configuration Render Blueprint
└── docker-compose.yml    # Services locaux (dev)

```

---

## Configuration Backend Django

### 1. Modèles de données

#### Modèles Identity & RBAC

**Fichier** : `backend/identity/models.py`

- `CoreIdentity` : Identité unique (email/téléphone uniques)
- `RbacRoleDef` : Définition des rôles système
- `IdentityRoleLink` : Lien identité ↔ rôle
- `SysAuditLog` : Journal d'audit (rôle actif enregistré)

**Caractéristiques** :
- Contraintes d'unicité (`db_index=True`, `unique=True`)
- `JSONField` pour permissions dynamiques
- `auditlog.register()` pour traçabilité
- Type hints Python + docstrings

#### Modèles Academic

**Fichier** : `backend/apps/academic/models.py`

- `Program` : Programme académique avec `academic_rules_json`
  - `cycle_type` : LMD / BTS / PhD
  - `grading_system` : min_validate, compensation, elimination_mark
  - `financial_rules` : mandatory_products, concours_required
  - `tutelle_export_format`
- `GradeEntry` : Notes étudiants

**Manager** : `ProgramManager.get_rules(filiere_code)` retourne JSON parsé

#### Modèles Finance

**Fichier** : `backend/apps/finance/models.py`

- `Invoice` : Factures avec numéro auto (`2026_FACT_SCOL_XXXX`)
- `Payment` : Paiements
- `FinancialLedger` : Grand livre
- `AccountingEntry` : Écritures comptables (double entrée)

**Méthodes** :
- `is_paid()` : Vérification paiement complet
- `is_blocked()` : Blocage si conditions non remplies

### 2. Middleware & Sécurité

#### ActiveRoleMiddleware

**Fichier** : `backend/core/middleware.py`

**Fonctionnalités** :
- Extraction `role_active` depuis :
  1. Header `X-Role-Active` (priorité haute)
  2. JWT payload (Keycloak)
  3. Session Django (fallback)
- Injection dans `request.role_active`
- Blocage SoD (Séparation des Tâches) :
  - `MANAGER_RH_PAY` ne peut pas valider sa propre opération

#### KeycloakJWTMiddleware

**Fichier** : `backend/core/middleware.py`

**Fonctionnalités** :
- Validation JWT via JWKS Keycloak
- Cache JWKS (300s par défaut)
- Décodage payload sans vérification (lecture-only)
- Extraction `role_active` depuis claims Keycloak

**Configuration** : `backend/core/settings.py`

```python
KEYCLOAK_CONFIG = {
    "server_url": os.getenv("KEYCLOAK_SERVER_URL", "https://keycloak-latest-j4gg.onrender.com"),
    "realm": os.getenv("KEYCLOAK_REALM", "iuec"),
    "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "backend-api"),
    "jwks_enabled": os.getenv("KEYCLOAK_JWKS_ENABLED", "1") == "1",
}
```

### 3. API REST (DRF)

#### Serializers & ViewSets

**Fichier** : `backend/api/serializers.py` + `backend/api/viewsets.py`

- `CoreIdentityViewSet` : Lecture seule (sauf `ADMIN_SI`)
- `IdentityRoleLinkViewSet` : CRUD (`ADMIN_SI`)
- `GradeEntryViewSet` : Saisie (`USER_TEACHER` + scope check)
- `InvoiceViewSet` : Gestion (`OPERATOR_FINANCE`)

#### Permissions personnalisées

**Fichier** : `backend/api/permissions.py`

- `ActiveRolePermission` : Vérification rôle actif
- `SoDPermission` : Blocage SoD violations
- `AdminSIPermission` : Accès admin système
- `OperatorFinancePermission` : Opérateur finance

**Swagger** : Intégration `drf-yasg` pour documentation auto

### 4. Services métiers

#### NoteCalculator

**Fichier** : `backend/apps/academic/services/note_calculator.py`

**Fonctionnalités** :
- Calcul moyenne pondérée (30% TD / 70% Exam par composant)
- Compensation entre UE (LMD)
- Notes bloquantes (TP < 10 → UE non validée)
- Seuils d'élimination
- Utilisation `Decimal` pour précision

**Règles dynamiques** : Chargement depuis `academic_rules_json`

#### FileNamer

**Fichier** : `backend/core/utils/file_namer.py`

**Pattern** : `[AAAA_MMDD]_[TYPE]_[ENTITE]_[REF]_[DETAIL].extension`

**Types** : `RELEVE`, `FACT`, `RECU`, `PV_JURY`, `CONTRAT`

**Normalisation** : Accents → ASCII, espaces → underscores

**PDF/A-3b** : Validation pour documents finaux

#### RBACChecker

**Fichier** : `backend/core/rbac/checker.py`

**Matrice de permissions** : Hardcodée ou JSON

**Actions** : lecture / C/U/D / validation / accès masqué

**Data masking** : Ex. salaire visible seulement `RECTEUR`/`DAF`/`SG`

---

## Configuration Frontend React

### 1. Contexte d'authentification

**Fichier** : `frontend/src/context/AuthContext.tsx`

**Types** :
```typescript
export type UserRole =
  | "RECTEUR"
  | "DAF"
  | "SG"
  | "ADMIN_SI"
  | "USER_TEACHER"
  | "ENSEIGNANT"
  | "OPERATOR_FINANCE";
```

**Fonctionnalités** :
- Gestion token JWT (localStorage)
- Rôle actif utilisateur
- État authentifié

### 2. Contexte de rôles

**Fichier** : `frontend/src/context/RoleContext.tsx`

**Fonctionnalités** :
- Liste rôles disponibles
- Rôle actif sélectionné
- Régénération JWT avec claim `role_active`
- API endpoint `/api/auth/regenerate-token/`

### 3. Composant RoleSwitcher

**Fichier** : `frontend/src/components/RoleSwitcher.tsx`

**UI** : Dropdown MUI pour sélection rôle actif

**Layout dynamique** :
- `RECTEUR` : KPI institutionnels
- `ENSEIGNANT` : Mes cours
- `DAF` : Budget global
- etc.

### 4. Service API

**Fichier** : `frontend/src/services/api.ts`

**Configuration Axios** :
```typescript
const api = axios.create({
  baseURL: "https://iuec-erp.onrender.com",
  timeout: 15000,
});
```

**Intercepteur** :
- Header `Authorization: Bearer <token>`
- Header `X-Role-Active: <role>`

### 5. Composant GradeGrid

**Fichier** : `frontend/src/pages/teacher/GradeGrid.tsx`

**Technologie** : `ag-grid-react`

**Fonctionnalités** :
- Colonnes : étudiant, CC, TP, Exam, moyenne
- Édition inline
- Navigation clavier
- Blocage si rôle ≠ `USER_TEACHER` ou hors scope
- Validation seuils (ex. TP < 10 → UE bloquée)
- API `/api/grades/bulk-update/`

---

## Déploiement Render - Backend

### 1. Configuration Dockerfile

**Fichier** : `backend/Dockerfile`

**Build multi-stage** :

```dockerfile
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Django backend
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

WORKDIR /app

# Install python-dotenv explicitement
RUN pip install --no-cache-dir python-dotenv==1.0.1

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend
WORKDIR /app/backend

# Copy React build from stage 1
COPY --from=frontend-build /app/frontend/build /app/backend/static/react

EXPOSE ${PORT}

CMD ["sh", "entrypoint.sh"]
```

**Optimisations** :
- Image `python:3.12-slim` (~500MB)
- `.dockerignore` pour exclure `.git`, `__pycache__`, `node_modules`
- Cache npm/pip pour builds rapides

### 2. Script entrypoint

**Fichier** : `backend/entrypoint.sh`

```bash
#!/usr/bin/env bash
set -e

python manage.py migrate
python manage.py collectstatic --noinput
gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
```

**Étapes** :
1. Migrations base de données
2. Collecte fichiers statiques
3. Démarrage Gunicorn

### 3. Configuration Render

**Fichier** : `render.yaml`

```yaml
services:
  - type: web
    name: iuec-backend
    env: docker
    repo: https://github.com/MartinJR91/iuec-erp
    branch: main
    dockerfilePath: ./backend/Dockerfile
    healthCheckPath: /health/
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: iuec-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: "false"
      - key: ALLOWED_HOSTS
        value: iuec-erp.onrender.com,localhost

  - type: postgres
    name: iuec-db
    plan: free
```

**Variables d'environnement** :
- `DATABASE_URL` : Auto-générée depuis PostgreSQL
- `SECRET_KEY` : Générée automatiquement
- `DEBUG` : `false` en production
- `ALLOWED_HOSTS` : Domaine Render + localhost

### 4. Configuration Django settings

**Fichier** : `backend/core/settings.py`

**Static files** :
```python
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_DIRS = [BASE_DIR / "static"]
```

**Database** :
```python
USE_SQLITE = os.getenv("USE_SQLITE", "0") == "1"
DATABASE_URL = os.getenv("DATABASE_URL")
if USE_SQLITE:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
elif DATABASE_URL and not LOCAL_DB_ONLY:
    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL, conn_max_age=600, ssl_require=True
    )
```

**CORS** :
```python
CORS_ALLOWED_ORIGINS = [
    "https://iuec-frontend.onrender.com",
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True
```

**Middleware** :
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.KeycloakJWTMiddleware",
    "core.middleware.ActiveRoleMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

### 5. Template SPA React

**Fichier** : `backend/templates/index.html`

**Fonctionnalités** :
- Chargement dynamique assets depuis `asset-manifest.json`
- Fallback `/static/react/asset-manifest.json` → `/static/asset-manifest.json`
- Injection CSS/JS automatique

```html
{% load static %}
<!DOCTYPE html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>IUEC-ERP</title>
    <link rel="icon" href="{% static 'react/favicon.ico' %}" />
    <script>
      async function loadReactAssets() {
        const primary = "{% static 'react/asset-manifest.json' %}";
        const fallback = "{% static 'asset-manifest.json' %}";
        const response = await fetch(primary).then((res) => (res.ok ? res : fetch(fallback)));
        if (!response.ok) return;
        const manifest = await response.json();
        const entrypoints = manifest.entrypoints || [];
        const base = response.url.replace("asset-manifest.json", "");
        entrypoints.forEach((entry) => {
          if (entry.endsWith(".css")) {
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = base + entry;
            document.head.appendChild(link);
          } else if (entry.endsWith(".js")) {
            const script = document.createElement("script");
            script.defer = true;
            script.src = base + entry;
            document.body.appendChild(script);
          }
        });
      }
      window.addEventListener("DOMContentLoaded", loadReactAssets);
    </script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
```

**Routing SPA** : `backend/core/urls.py`

```python
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("health/", health),
    re_path(r"^(?!static|media|admin|api|health).+$", TemplateView.as_view(template_name="index.html")),
    path("", TemplateView.as_view(template_name="index.html")),
]
```

---

## Déploiement Render - Keycloak

### 1. Configuration Render

**Service** : `keycloak:latest`

**Type** : Web Service (Docker)

**Image** : `quay.io/keycloak/keycloak:latest`

**Docker Command** : `/opt/keycloak/bin/kc.sh start --optimized`

**Variables d'environnement** :
- `KC_HTTP_PORT` : `10000`
- `KC_HOSTNAME` : `keycloak-latest-j4gg.onrender.com`
- `KC_HOSTNAME_STRICT` : `false`
- `KC_HTTP_RELATIVE_PATH` : `/`
- `KC_DB` : `dev-file` (H2 en mémoire pour free tier)
- `KC_HEALTH_ENABLED` : `true`
- `JAVA_OPTS` : `-Xms128m -Xmx384m` (limite mémoire free tier)

**Profile** : `prod`

### 2. Limitations free tier

- **Mémoire** : 512MB max (d'où `JAVA_OPTS` pour limiter)
- **Base de données** : H2 en mémoire (données perdues au redémarrage)
- **Sleep** : Instance s'endort après inactivité (~50s de délai)

### 3. Configuration Realm

**Realm** : `iuec`

**Clients** :
- `web-app` : Frontend React (public)
- `backend-api` : Backend Django (confidential)

**Rôles Realm** :
- `RECTEUR`
- `DAF`
- `SG`
- `ADMIN_SI`
- `USER_TEACHER`
- `ENSEIGNANT`
- `OPERATOR_FINANCE`

**Mappers** :
- `role_active` : Claim JWT pour rôle actif

---

## Logs de déploiement

### Logs Backend (iuec-erp)

```
==> Setting WEB_CONCURRENCY=1 by default, based on available CPUs in the instance
==> Deploying...
Operations to perform:
  Apply all migrations: academic, admin, auditlog, auth, contenttypes, core_identity, finance, guardian, identity, rbac, rh, sessions
Running migrations:
  No migrations to apply.
3 static files copied to '/app/backend/staticfiles', 206 unmodified.
[2026-01-27 15:50:20 +0000] [26] [INFO] Starting gunicorn 22.0.0
[2026-01-27 15:50:20 +0000] [26] [INFO] Listening at: http://0.0.0.0:10000 (26)
[2026-01-27 15:50:20 +0000] [26] [INFO] Using worker: sync
[2026-01-27 15:50:20 +0000] [27] [INFO] Booting worker with pid: 27
[2026-01-27 15:50:20 +0000] [28] [INFO] Booting worker with pid: 28
==> Your service is live 🎉
==> 
==> ///////////////////////////////////////////////////////////
==> 
==> Available at your primary URL https://iuec-erp.onrender.com
==> 
==> ///////////////////////////////////////////////////////////
```

**Analyse** :
- ✅ Migrations OK (aucune nouvelle)
- ✅ Collectstatic OK (3 nouveaux fichiers, 206 inchangés)
- ✅ Gunicorn démarré (2 workers)
- ✅ Service accessible sur port 10000

### Logs Keycloak

```
==> Setting WEB_CONCURRENCY=1 by default, based on available CPUs in the instance
==> Starting service...
JAVA_OPTS already set in environment; overriding default settings
Changes detected in configuration. Updating the server image.
WARNING: Usage of the default value for the db option in the production profile is deprecated. Please explicitly set the db instead.
WARNING: Hostname v1 options [proxy] are still in use, please review your configuration
Updating the configuration and installing your custom providers, if any. Please wait.
==> No open ports detected, continuing to scan...
2026-01-27 15:52:19,162 INFO  [io.quarkus.deployment.QuarkusAugmentor] (main) Quarkus augmentation completed in 178209ms
Server configuration updated and persisted. Run the following command to review the configuration:
	kc.sh show-config
Next time you run the server, just run:
	kc.sh start --optimized
WARNING: Hostname v1 options [proxy] are still in use, please review your configuration
2026-01-27 15:52:50,454 INFO  [org.keycloak.url.HostnameV2ProviderFactory] (main) If hostname is specified, hostname-strict is effectively ignored
2026-01-27 15:53:40,167 INFO  [org.hibernate.orm.jdbc.batch] (JPA Startup Thread) HHH100501: Automatic JDBC statement batching enabled (maximum batch size 32)
2026-01-27 15:54:00,356 INFO  [org.keycloak.quarkus.runtime.storage.database.liquibase.QuarkusJpaUpdaterProvider] (main) Initializing database schema. Using changelog META-INF/jpa-changelog-master.xml
2026-01-27 15:55:08,859 INFO  [org.infinispan.CONTAINER] (main) ISPN000556: Starting user marshaller 'org.infinispan.commons.marshall.ImmutableProtoStreamMarshaller'
2026-01-27 15:55:15,555 INFO  [org.keycloak.connections.infinispan.DefaultInfinispanConnectionProviderFactory] (main) Node name: node_467424, Site name: null
2026-01-27 15:55:19,752 INFO  [org.keycloak.services] (main) KC-SERVICES0050: Initializing master realm
2026-01-27 15:55:58,750 INFO  [org.keycloak.services] (main) KC-SERVICES0077: Created temporary admin user with username admin
2026-01-27 15:56:02,253 INFO  [io.quarkus] (main) Keycloak 26.5.2 on JVM (powered by Quarkus 3.27.2) started in 221.595s. Listening on: http://0.0.0.0:10000
2026-01-27 15:56:02,253 INFO  [io.quarkus] (main) Profile prod activated. 
2026-01-27 15:56:02,254 INFO  [io.quarkus] (main) Installed features: [agroal, cdi, hibernate-orm, hibernate-validator, jdbc-h2, keycloak, narayana-jta, opentelemetry, reactive-routes, rest, rest-jackson, smallrye-context-propagation, vertx]
==> Your service is live 🎉
==> 
==> ///////////////////////////////////////////////////////////
==> 
==> Available at your primary URL https://keycloak-latest-j4gg.onrender.com
==> 
==> ///////////////////////////////////////////////////////////
```

**Analyse** :
- ⚠️ Warnings hostname v1 (non bloquant)
- ✅ Quarkus augmentation OK (~178s)
- ✅ Base de données H2 initialisée
- ✅ Realm master initialisé
- ✅ Admin temporaire créé (`admin`)
- ✅ Keycloak démarré (~221s)
- ✅ Profile `prod` activé
- ✅ Service accessible sur port 10000

**Temps de démarrage** : ~3-4 minutes (normal pour free tier)

---

## Commandes Git

### 1. Configuration initiale

```powershell
cd C:\Users\HP\iuec-erp
git init
git remote add origin https://github.com/MartinJR91/iuec-erp.git
```

### 2. Commit & Push

```powershell
# Vérifier l'état
git status -s

# Ajouter fichiers modifiés
git add .

# Commit
git commit -m "Description des changements"

# Push
git push origin main
```

### 3. Nettoyage artefacts build

```powershell
# Supprimer dossiers générés
Remove-Item -Recurse -Force backend\static\react, backend\staticfiles, frontend\build

# Retirer du suivi Git
git rm -r --cached backend\static\react backend\staticfiles

# Commit nettoyage
git add .gitignore
git commit -m "Clean build artifacts and ignore static outputs"
git push origin main
```

### 4. Règles .gitignore

**Fichier** : `.gitignore`

```
# Python / Django
__pycache__/
*.py[cod]
*.sqlite3
.venv/
venv/
.env

# Node / React
node_modules/
build/
dist/

# Static files (générés)
backend/static/react/
backend/staticfiles/
frontend/build/
```

---

## Troubleshooting

### 1. Erreur `ModuleNotFoundError: No module named 'pkg_resources'`

**Cause** : `setuptools` manquant dans Docker

**Solution** : Ajouter dans `Dockerfile` :
```dockerfile
RUN pip install --no-cache-dir setuptools==75.6.0
```

### 2. Erreur `connection to server at "127.0.0.1", port 5432 failed`

**Cause** : `DATABASE_URL` non configurée ou SQLite utilisé localement

**Solution** :
```powershell
# Local : utiliser SQLite
$env:USE_SQLITE = "1"
$env:LOCAL_DB_ONLY = "1"
python manage.py migrate
```

### 3. Erreur `404 Not Found` pour `/static/react/asset-manifest.json`

**Cause** : Manifest collecté à `/static/asset-manifest.json` au lieu de `/static/react/`

**Solution** : Template avec fallback (déjà implémenté)

### 4. Erreur Keycloak `Out of memory (used over 512Mi)`

**Cause** : Limite mémoire free tier dépassée

**Solution** : Ajouter variable d'environnement :
```
JAVA_OPTS=-Xms128m -Xmx384m
```

### 5. Erreur `Invalid value for option 'KC_HTTP_PORT': Expected an integer`

**Cause** : Variable `KC_HTTP_PORT` contient `$PORT` au lieu d'un entier

**Solution** : Définir `KC_HTTP_PORT=10000` (entier)

### 6. Page blanche sur `/`

**Cause** : Assets React non chargés

**Solution** :
1. Vérifier `STATICFILES_DIRS` dans `settings.py`
2. Vérifier `homepage` dans `frontend/package.json` (`"/static/react"`)
3. Vérifier template `index.html` avec fallback

---

## Checklist de déploiement

### Pré-déploiement

- [ ] Code commité et poussé sur GitHub
- [ ] `.gitignore` configuré (exclure `staticfiles/`, `build/`)
- [ ] `Dockerfile` testé localement
- [ ] `entrypoint.sh` exécutable (`chmod +x`)
- [ ] Variables d'environnement documentées

### Configuration Render

- [ ] Service backend créé (Docker)
- [ ] Service Keycloak créé (Docker)
- [ ] Base de données PostgreSQL créée (free tier)
- [ ] Variables d'environnement configurées :
  - [ ] `DATABASE_URL` (auto depuis PostgreSQL)
  - [ ] `SECRET_KEY` (générée)
  - [ ] `DEBUG=false`
  - [ ] `ALLOWED_HOSTS`
  - [ ] `KEYCLOAK_SERVER_URL`
  - [ ] `KEYCLOAK_REALM`
  - [ ] `KEYCLOAK_CLIENT_ID`

### Build & Deploy

- [ ] Build Docker réussi (backend)
- [ ] Build Docker réussi (Keycloak)
- [ ] Migrations appliquées (`python manage.py migrate`)
- [ ] Static files collectés (`collectstatic`)
- [ ] Gunicorn démarré (2 workers)
- [ ] Health check OK (`/health/`)

### Post-déploiement

- [ ] Backend accessible : `https://iuec-erp.onrender.com`
- [ ] Keycloak accessible : `https://keycloak-latest-j4gg.onrender.com`
- [ ] Frontend React chargé (`/dashboard`)
- [ ] API fonctionnelle (`/api/identity/`)
- [ ] Authentification Keycloak OK
- [ ] Rôles actifs fonctionnels

### Tests fonctionnels

- [ ] Login utilisateur
- [ ] Sélection rôle actif
- [ ] Dashboard selon rôle
- [ ] API avec authentification
- [ ] SoD violations bloquées
- [ ] Audit log enregistré

---

## Conclusion

Le déploiement IUEC-ERP sur Render est **opérationnel** avec :

✅ **Backend Django** : Service web Docker multi-stage  
✅ **Frontend React** : SPA servi par Django  
✅ **Keycloak** : Authentification OIDC/JWT  
✅ **PostgreSQL** : Base de données (free tier)  
✅ **Static files** : WhiteNoise + collectstatic  
✅ **Health check** : Endpoint `/health/`  

**URLs de production** :
- Backend : `https://iuec-erp.onrender.com`
- Keycloak : `https://keycloak-latest-j4gg.onrender.com`

**Limitations free tier** :
- Sleep après inactivité (~50s délai)
- 512MB RAM max
- Base Keycloak H2 (données perdues au redémarrage)

**Prochaines étapes** :
- Migration Keycloak vers PostgreSQL externe
- Upgrade plan Render (Starter) pour performance
- Monitoring & alertes (Sentry, etc.)

---

**Document généré le** : 27 janvier 2026  
**Version** : 1.0
