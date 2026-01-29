# ✅ Checklist de Tests - IUEC-ERP

## 🚀 Serveurs
- [ ] Backend Django démarré sur `http://localhost:8000`
- [ ] Frontend React démarré sur `http://localhost:3000`
- [ ] Pas d'erreurs dans les consoles backend/frontend

---

## 🔐 1. Authentification et Rôles

### Login
- [ ] Accès à `/login` fonctionne
- [ ] Login avec `recteur@iuec.cm` / `recteur123!` → succès
- [ ] Login avec identifiants incorrects → erreur 401
- [ ] Redirection automatique vers `/dashboard` après login

### Changement de Rôle (RoleSwitcher)
- [ ] Le sélecteur de rôle apparaît dans l'AppBar
- [ ] Liste des rôles disponibles s'affiche
- [ ] Changement de rôle sans logout → succès
- [ ] Le dashboard s'adapte au rôle actif
- [ ] Le header `X-Role-Active` est envoyé dans les requêtes API

### Dark Mode
- [ ] Le toggle dark mode apparaît dans l'AppBar
- [ ] Clic sur le toggle → changement de thème
- [ ] Le thème est persisté dans `localStorage`
- [ ] Pas de flash au rechargement de page

---

## 📊 2. Dashboard

### Dashboard RECTEUR
- [ ] Accès à `/dashboard` avec rôle RECTEUR
- [ ] KPI Cards affichées :
  - [ ] Nombre d'étudiants inscrits
  - [ ] Revenus du mois
  - [ ] Alertes SoD
  - [ ] Taux d'assiduité
- [ ] Graphique d'évolution des inscriptions affiché
- [ ] Boutons "Gérer les facultés" et "Gérer les étudiants" visibles
- [ ] Section "Reporting stratégique" affichée (si données disponibles)
- [ ] Toast d'alerte SoD si nouvelle alerte détectée

### Dashboard DOYEN/VALIDATOR_ACAD
- [ ] Accès à `/dashboard` avec rôle DOYEN
- [ ] Section "Pilotage académique" affichée
- [ ] Boutons "Gérer les étudiants" et "PV Jury" visibles
- [ ] Bouton "Ouvrir la gestion des facultés" fonctionne

### Dashboard SCOLARITE
- [ ] Accès à `/dashboard` avec rôle SCOLARITE → **TESTER avec `scolarite@iuec.cm` / `scol123!`**
- [ ] Section "Gestion de la scolarité" affichée
- [ ] Bouton "Inscrire / Gérer étudiants" visible et fonctionne
- [ ] Card "Actions rapides" avec boutons "Liste des étudiants" et "Nouvelle inscription"

### Dashboard OPERATOR_FINANCE
- [ ] Accès à `/dashboard` avec rôle OPERATOR_FINANCE
- [ ] Section "Gestion financière" affichée
- [ ] Liste des factures impayées affichée
- [ ] Bouton "Étudiants bloqués" visible et fonctionne

### Dashboard USER_STUDENT
- [ ] Accès à `/dashboard` avec rôle USER_STUDENT
- [ ] Section "Mon tableau de bord étudiant" affichée
- [ ] Card "Solde à payer" affichée avec couleur appropriée
- [ ] Boutons "Mon dossier" et "Mes notes" visibles et fonctionnent

---

## 👥 3. Gestion des Étudiants (`/students`)

### Vue RECTEUR
- [ ] Accès à `/students` avec rôle RECTEUR
- [ ] Liste globale de tous les étudiants affichée
- [ ] KPI Cards affichées :
  - [ ] Total étudiants
  - [ ] Nombre d'étudiants bloqués
  - [ ] Pourcentage d'étudiants bloqués
  - [ ] Liste des facultés
- [ ] Filtre par faculté fonctionne
- [ ] Recherche (matricule, nom, prénom, email) fonctionne
- [ ] Pagination fonctionne (10, 25, 50, 100)
- [ ] Colonnes DataGrid :
  - [ ] Matricule
  - [ ] Nom / Prénom
  - [ ] Programme
  - [ ] Niveau
  - [ ] Statut Finance (chips colorés)
  - [ ] Statut Académique
  - [ ] Solde (format XAF)
- [ ] Clic sur une ligne → Modal de détail s'ouvre
- [ ] Modal affiche : profil, inscriptions, statut finance

### Vue DOYEN/VALIDATOR_ACAD
- [ ] Accès à `/students` avec rôle DOYEN
- [ ] Liste filtrée automatiquement par faculté du DOYEN
- [ ] Bouton "Valider les inscriptions sélectionnées" visible
- [ ] Sélection multiple d'étudiants fonctionne
- [ ] Validation d'inscription → toast de succès
- [ ] Données rafraîchies après validation

### Vue SCOLARITE
- [ ] Accès à `/students` avec rôle SCOLARITE
- [ ] Liste complète des étudiants affichée
- [ ] Bouton "Inscrire un étudiant" visible (placeholder)
- [ ] Bouton "Modifier statut" dans les actions de ligne

### Vue OPERATOR_FINANCE
- [ ] Accès à `/students` avec rôle OPERATOR_FINANCE
- [ ] Liste filtrée sur étudiants bloqués/moratoire
- [ ] Bouton "Débloquer (Moratoire)" visible dans les actions
- [ ] Déblocage → toast de succès + statut mis à jour

### Vue USER_STUDENT
- [ ] Accès à `/students` avec rôle USER_STUDENT
- [ ] Vue simplifiée : Card avec profil personnel
- [ ] Affichage du solde coloré (vert si OK, rouge si bloqué)
- [ ] Bouton "Payer" visible (placeholder)
- [ ] Impossible d'accéder aux autres profils (404/403)

### Fonctionnalités Générales
- [ ] Toast notifications fonctionnent (succès/erreur)
- [ ] Chargement (loading) affiché pendant les requêtes
- [ ] Gestion des erreurs API (messages d'erreur affichés)
- [ ] Responsive design (test sur mobile/tablette)

---

## 🏛️ 4. Gestion des Facultés (`/faculties`)

### Vue RECTEUR/ADMIN_SI
- [ ] Accès à `/faculties` avec rôle RECTEUR
- [ ] Liste des facultés affichée
- [ ] CRUD complet fonctionne :
  - [ ] Création d'une faculté
  - [ ] Modification d'une faculté
  - [ ] Suppression d'une faculté
- [ ] Inline programmes dans l'admin Django
- [ ] Édition JSON rules fonctionne

### Vue DOYEN/VALIDATOR_ACAD
- [ ] Accès à `/faculties` avec rôle DOYEN
- [ ] Édition des règles JSON pour sa faculté
- [ ] Validation du format JSON fonctionne

---

## 📝 5. Gestion des Notes (`/notes`)

### Vue USER_TEACHER/ENSEIGNANT
- [ ] Accès à `/notes` avec rôle USER_TEACHER
- [ ] Sélecteur de cours fonctionne
- [ ] Table ag-grid éditable affichée
- [ ] Colonnes : Étudiant, CC, TP, Exam, Moyenne (auto-calculée)
- [ ] Sauvegarde par composante fonctionne
- [ ] Toast de confirmation après sauvegarde

### Vue VALIDATOR_ACAD
- [ ] Accès à `/notes` avec rôle VALIDATOR_ACAD
- [ ] Vue PV Jury affichée
- [ ] Bouton "Clôturer" visible
- [ ] Clôture → toast de succès + données rafraîchies

### Vue USER_STUDENT
- [ ] Accès à `/notes` avec rôle USER_STUDENT
- [ ] Vue lecture seule de ses notes
- [ ] Affichage des moyennes et statuts UE

---

## 🔄 6. Workflows et Interactions

### Workflow Jury
- [ ] TEACHER saisit notes → succès
- [ ] VALIDATOR_ACAD valide PV → succès
- [ ] SCOLARITE peut éditer certificats (si implémenté)

### Blocage Inscription
- [ ] OPERATOR_FINANCE bloque un étudiant (`finance_status = 'Bloqué'`)
- [ ] L'étudiant ne peut pas s'inscrire (erreur 400)
- [ ] L'étudiant ne voit pas ses cours (si implémenté)

### Alerte SoD
- [ ] Détection de conflit SoD (ex: RH_PAY valide son salaire)
- [ ] Email/log envoyé au RECTEUR (si configuré)
- [ ] Alerte affichée sur le dashboard RECTEUR

---

## 🧪 7. Tests Backend (Pytest)

### Exécution des Tests
- [ ] `pytest tests/test_students.py -v` → 7/7 tests passent
- [ ] `pytest tests/test_students_api.py -v` → tous les tests passent
- [ ] `pytest tests/test_auth.py -v` → tous les tests passent
- [ ] `pytest tests/test_views_endpoints.py -v` → tous les tests passent
- [ ] `pytest --cov` → couverture > 80% (ou acceptable)

### Tests Spécifiques Étudiants
- [ ] `test_student_profile_creation_and_sync` → passe
- [ ] `test_registration_blocked_finance` → passe
- [ ] `test_student_self_access_only` → passe
- [ ] `test_doyen_scope_filter` → passe
- [ ] `test_finance_deblock` → passe
- [ ] `test_validation_registration_by_validator` → passe
- [ ] `test_solde_calculation_signal` → passe

---

## 🔌 8. API Endpoints

### Endpoints Étudiants
- [ ] `GET /api/students/` → 200 avec rôle actif
- [ ] `GET /api/students/<uuid>/` → 200 avec détails complets
- [ ] `POST /api/students/` → 201 (inscription annuelle)
- [ ] `PUT /api/students/<uuid>/finance-status/` → 200 (OPERATOR_FINANCE)
- [ ] `POST /api/students/<uuid>/validate-registration/` → 200 (VALIDATOR_ACAD)
- [ ] Filtrage par rôle fonctionne correctement

### Endpoints Dashboard
- [ ] `GET /api/dashboard/` avec RECTEUR → 200 + KPIs
- [ ] `GET /api/dashboard/` avec USER_STUDENT → 200 + données limitées
- [ ] `GET /api/dashboard/` avec USER_TEACHER → 200 + données limitées

### Endpoints Facultés
- [ ] `GET /api/faculties/` → 200
- [ ] `POST /api/faculties/` → 201 (ADMIN_SI/VALIDATOR_ACAD)
- [ ] `PUT /api/faculties/<id>/` → 200

### Authentification
- [ ] `POST /api/token/` → 200 avec identifiants valides
- [ ] `POST /api/token/` → 401 avec identifiants invalides
- [ ] Token JWT valide pour les requêtes authentifiées

---

## 🎨 9. Interface Utilisateur

### Navigation
- [ ] Liens dans le dashboard fonctionnent
- [ ] Navigation entre pages sans erreur
- [ ] Breadcrumbs (si implémentés) affichés

### Responsive Design
- [ ] Affichage correct sur desktop (1920x1080)
- [ ] Affichage correct sur tablette (768x1024)
- [ ] Affichage correct sur mobile (375x667)
- [ ] Menu hamburger (si implémenté) fonctionne

### Accessibilité
- [ ] Contraste des couleurs suffisant
- [ ] Navigation au clavier fonctionne
- [ ] Labels ARIA présents (si implémentés)

---

## 🐛 10. Gestion des Erreurs

### Erreurs Frontend
- [ ] Erreur 401 → redirection vers `/login`
- [ ] Erreur 403 → message d'erreur affiché
- [ ] Erreur 404 → message d'erreur affiché
- [ ] Erreur 500 → message d'erreur générique affiché
- [ ] Timeout réseau → message d'erreur affiché

### Erreurs Backend
- [ ] Validation des données → messages d'erreur clairs
- [ ] Contraintes DB → messages d'erreur appropriés
- [ ] Logs d'erreur dans la console backend

---

## 📱 11. Performance

### Temps de Chargement
- [ ] Dashboard se charge en < 2 secondes
- [ ] Liste des étudiants se charge en < 3 secondes
- [ ] Pas de lag lors de la saisie dans les formulaires

### Optimisations
- [ ] Pagination fonctionne (pas de chargement de toutes les données)
- [ ] Images/assets optimisés
- [ ] Pas de requêtes API inutiles

---

## 🔒 12. Sécurité

### Authentification
- [ ] Token JWT expire après délai configuré
- [ ] Refresh token fonctionne (si implémenté)
- [ ] Déconnexion invalide le token

### Permissions
- [ ] RECTEUR peut accéder à toutes les ressources
- [ ] DOYEN ne peut accéder qu'à sa faculté
- [ ] USER_STUDENT ne peut accéder qu'à son profil
- [ ] OPERATOR_FINANCE peut modifier finance_status uniquement

### SoD (Separation of Duties)
- [ ] Conflits SoD détectés
- [ ] Alertes SoD envoyées au RECTEUR
- [ ] Actions bloquées en cas de conflit

---

## 📊 13. Données et Persistance

### LocalStorage
- [ ] Thème dark mode persisté
- [ ] Rôle actif persisté (si implémenté)
- [ ] Pas de données sensibles dans localStorage

### Base de Données
- [ ] Migrations appliquées
- [ ] Données de test disponibles (seed)
- [ ] Contraintes DB respectées

---

## ✅ 14. Checklist Finale

### Avant Déploiement
- [ ] Tous les tests passent
- [ ] Pas d'erreurs dans les consoles
- [ ] Documentation à jour
- [ ] README.md à jour
- [ ] Variables d'environnement configurées
- [ ] Build frontend réussi (`npm run build`)
- [ ] Collectstatic réussi (`python manage.py collectstatic`)

### Tests de Régression
- [ ] Anciennes fonctionnalités toujours fonctionnelles
- [ ] Pas de régression visuelle
- [ ] Pas de régression de performance

---

## 📝 Notes

- **Priorité Haute** : Tests marqués avec ⚠️
- **Priorité Moyenne** : Tests standards
- **Priorité Basse** : Tests optionnels (améliorations futures)

---

**Date de création** : 2026-01-29  
**Dernière mise à jour** : 2026-01-29
