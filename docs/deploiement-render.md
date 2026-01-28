# Déploiement Render — Récapitulatif complet (point par point)

## 1) Objectif
Déployer l’ERP (Django + React) sur Render avec un backend Dockerisé, un front servi par Django, et Keycloak en service séparé.

## 2) Architecture cible
- Backend Django en service Web (Docker).
- Frontend React compilé puis servi via Django (staticfiles).
- Keycloak déployé sur un service Render séparé.
- Base PostgreSQL Render pour la prod.

## 3) Modifications techniques principales
1. **Backend/Django**
   - Configuration `STATIC_URL` et `STATICFILES_DIRS` pour servir React via `/static/`.
   - Intégration `whitenoise` et `collectstatic`.
   - Endpoint `/health/` pour Render.
2. **Frontend/React**
   - Build React intégré au pipeline Docker (multi‑stage).
   - `homepage` fixé à `/static/react` pour générer les assets avec le bon prefix.
3. **Template SPA**
   - Chargement dynamique des assets via `asset-manifest.json`.
   - Fallback automatique si le manifest est servi à `/static/asset-manifest.json`.
4. **Docker/Render**
   - Dockerfile multi‑stage (build React puis copie dans Django).
   - `entrypoint.sh` : migrate + collectstatic + gunicorn.
   - `render.yaml` : web service + static + postgres.
5. **Nettoyage repo**
   - Suppression des artefacts générés (`backend/static/react`, `backend/staticfiles`, `frontend/build`).
   - Ajout de règles `.gitignore` pour éviter ces fichiers à l’avenir.

## 4) Commandes locales exécutées (extrait)
```
git add backend/templates/index.html
git commit -m "Fallback asset-manifest path for Render"
git log -1 --stat -- backend/templates/index.html

git rm -r --cached backend/static/react backend/staticfiles
Remove-Item -Recurse -Force backend\static\react, backend\staticfiles, frontend\build
git add .gitignore backend/core/settings.py frontend/package.json
git add -u
git commit -m "Clean build artifacts and ignore static outputs"
git push origin main
```

## 5) Validation fonctionnelle
- `https://iuec-erp.onrender.com/` redirige vers `/dashboard`.
- `/dashboard` affiche l’interface React (KPI, rôle actif, etc.).
- `https://iuec-erp.onrender.com/static/asset-manifest.json` renvoie un manifest valide.
- `https://iuec-erp.onrender.com/static/react/asset-manifest.json` peut rester 404 (fallback OK).

## 6) Logs Render — Keycloak (extraits fournis)
```
==> Starting service...
WARNING: Usage of the default value for the db option in the production profile is deprecated.
==> No open ports detected, continuing to scan...
2026-01-27 15:56:02,253 INFO  [io.quarkus] Keycloak 26.5.2 ... Listening on: http://0.0.0.0:10000
2026-01-27 15:56:02,253 INFO  [io.quarkus] Profile prod activated.
==> Your service is live 🎉
==> Available at your primary URL https://keycloak-latest-j4gg.onrender.com
```

## 7) Logs Render — Backend iuec-erp (extraits fournis)
```
==> Deploying...
Operations to perform:
  Apply all migrations: academic, admin, auditlog, auth, contenttypes, core_identity, finance, guardian, identity, rbac, rh, sessions
Running migrations:
  No migrations to apply.
3 static files copied to '/app/backend/staticfiles', 206 unmodified.
[2026-01-27 15:50:20 +0000] [26] [INFO] Starting gunicorn 22.0.0
[2026-01-27 15:50:20 +0000] [26] [INFO] Listening at: http://0.0.0.0:10000 (26)
==> Your service is live 🎉
==> Available at your primary URL https://iuec-erp.onrender.com
```

## 8) Points d’attention / recommandations
- Les avertissements Keycloak “Hostname v1 options [proxy]” sont connus et non bloquants.
- Sur Render free tier, la mise en veille peut ajouter ~50s de latence au premier accès.
- Les artefacts build ne doivent pas être commités ; ils sont générés à chaque déploiement.

## 9) Références d’URLs
- Backend : https://iuec-erp.onrender.com
- Dashboard : https://iuec-erp.onrender.com/dashboard
- Manifest : https://iuec-erp.onrender.com/static/asset-manifest.json
- Keycloak : https://keycloak-latest-j4gg.onrender.com
