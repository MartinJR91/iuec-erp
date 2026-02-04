# 🧪 Test Complet des Fonctionnalités - IUEC ERP

**Date de test :** _______________  
**Testeur :** _______________  
**Version :** _______________

---

## 📋 Instructions

Pour chaque section, cochez ✅ si le test passe, ❌ si le test échoue, ou ⚠️ si partiel/à améliorer.  
**Notez les erreurs et améliorations dans la section "Observations" à la fin du document.**

---

## 🚀 1. Configuration et Démarrage

### 1.1 Serveurs
- [ ] Backend Django démarré sur `http://127.0.0.1:8000`
- [ ] Frontend React démarré sur `http://localhost:3000`
- [ ] Pas d'erreurs dans la console backend
- [ ] Pas d'erreurs dans la console frontend (F12)
- [ ] Pas d'erreurs dans la console réseau (onglet Network)

### 1.2 Base de données
- [ ] Base de données accessible
- [ ] Migrations appliquées (`python manage.py migrate`)
- [ ] Données de test disponibles (seed)

---

## 🔐 2. Authentification et Gestion des Rôles

### 2.1 Page de Login (`/login`)
- [ ] Page accessible sans authentification
- [ ] Formulaire de connexion affiché correctement
- [ ] Champs email et mot de passe présents
- [ ] Bouton "Se connecter" fonctionnel

### 2.2 Connexion avec différents utilisateurs

#### Recteur
- [ ] Email : `recteur@iuec.cm` / Mot de passe : `recteur123!`
- [ ] Connexion réussie
- [ ] Redirection vers `/dashboard`
- [ ] Token JWT stocké dans localStorage

#### Enseignant
- [ ] Email : `marie.dupont@iuec.cm` / Mot de passe : `ens123!`
- [ ] Connexion réussie
- [ ] Redirection vers `/dashboard`

#### Étudiant
- [ ] Email : `elise.ngono@iuec.cm` / Mot de passe : `etu123!`
- [ ] Connexion réussie
- [ ] Redirection vers `/dashboard`

#### Finance
- [ ] Email : `finance@iuec.cm` / Mot de passe : `fin123!`
- [ ] Connexion réussie
- [ ] Redirection vers `/dashboard`

### 2.3 Gestion des erreurs de connexion
- [ ] Email incorrect → Message d'erreur affiché
- [ ] Mot de passe incorrect → Message d'erreur affiché
- [ ] Champs vides → Validation côté client
- [ ] Toast d'erreur affiché (react-hot-toast)

### 2.4 Changement de Rôle (RoleSwitcher)
- [ ] Sélecteur de rôle visible dans l'AppBar
- [ ] Liste des rôles disponibles s'affiche au clic
- [ ] Changement de rôle sans déconnexion
- [ ] Dashboard s'adapte au nouveau rôle
- [ ] Header `X-Role-Active` mis à jour dans les requêtes API
- [ ] Toast de confirmation affiché

### 2.5 Déconnexion
- [ ] Bouton "Déconnexion" visible dans l'AppBar
- [ ] Clic sur déconnexion → Redirection vers `/login`
- [ ] Token supprimé du localStorage
- [ ] Accès aux pages protégées bloqué après déconnexion

### 2.6 Protection des Routes
- [ ] Accès à `/dashboard` sans token → Redirection vers `/login`
- [ ] Accès à `/students` sans token → Redirection vers `/login`
- [ ] Accès à `/notes` sans token → Redirection vers `/login`
- [ ] Accès à `/faculties` sans token → Redirection vers `/login`

---

## 📊 3. Dashboard

### 3.1 Dashboard RECTEUR / DAF / SG / ADMIN_SI

#### Affichage
- [ ] Accès à `/dashboard` avec rôle RECTEUR
- [ ] Titre "Tableau de bord institutionnel" affiché
- [ ] Boutons "Gérer les facultés" et "Gérer les étudiants" visibles

#### KPI Cards
- [ ] **KPI Étudiants inscrits**
  - [ ] Valeur affichée correctement
  - [ ] Format avec séparateurs (ex: 1 234)
  - [ ] Icône People affichée
  - [ ] Trend "up" avec texte "+5% vs mois dernier"

- [ ] **KPI Revenus du mois**
  - [ ] Montant affiché avec format XAF
  - [ ] Icône AttachMoney affichée
  - [ ] Trend "up" avec texte "+12% vs décembre"

- [ ] **KPI Alertes SoD**
  - [ ] Nombre d'alertes affiché
  - [ ] Icône Warning affichée
  - [ ] Couleur rouge si alertes > 0, verte sinon
  - [ ] Toast d'alerte si nouvelle alerte détectée

- [ ] **KPI Taux d'assiduité**
  - [ ] Pourcentage affiché (ex: 92%)
  - [ ] Icône TrendingUp affichée
  - [ ] Trend "up" avec texte "+2% vs trimestre dernier"

#### Graphique
- [ ] Graphique d'évolution des inscriptions affiché
- [ ] Titre "Évolution des inscriptions (2025-2026)"
- [ ] Données affichées correctement
- [ ] Graphique responsive (s'adapte à la taille de l'écran)

#### Section Reporting Stratégique
- [ ] Section affichée si données disponibles
- [ ] Répartition par faculté affichée
- [ ] Graphique de répartition visible

### 3.2 Dashboard USER_TEACHER / ENSEIGNANT

#### Affichage
- [ ] Accès à `/dashboard` avec rôle USER_TEACHER
- [ ] Titre "Mes cours" affiché
- [ ] Bouton "Saisie notes" visible et fonctionnel

#### Liste des Cours
- [ ] Tableau des cours affiché
- [ ] Colonnes : Code, Nom du cours, Nb étudiants, Prochain cours
- [ ] Données des cours chargées depuis l'API
- [ ] Chips colorés pour les codes de cours

#### Statistiques
- [ ] Card "Mes statistiques" affichée
- [ ] "Étudiants notés" affiché (ex: 85 / 120)
- [ ] Barre de progression affichée
- [ ] Pourcentage calculé correctement

### 3.3 Dashboard USER_STUDENT

#### Affichage
- [ ] Accès à `/dashboard` avec rôle USER_STUDENT
- [ ] Titre "Mon tableau de bord étudiant" affiché
- [ ] Boutons "Mon dossier" et "Mes notes" visibles

#### Notes Récentes
- [ ] Tableau des notes affichées
- [ ] Colonnes : UE, Moyenne, Statut
- [ ] Chips pour les codes UE
- [ ] Moyennes affichées avec format "/20"
- [ ] Statuts colorés (vert = Validée, rouge = Ajourné)
- [ ] Message "Aucune note disponible" si pas de notes

#### Solde à Payer
- [ ] Card "Solde à payer" affichée
- [ ] Montant affiché avec format XAF
- [ ] Couleur verte si solde <= 0, rouge si solde > 0
- [ ] Bouton "Payer en ligne" affiché si solde > 0
- [ ] Chip "Aucun solde dû" affiché si solde <= 0

### 3.4 Dashboard OPERATOR_FINANCE

#### Affichage
- [ ] Accès à `/dashboard` avec rôle OPERATOR_FINANCE
- [ ] Titre "Tableau de bord Finance" affiché

#### Factures Impayées
- [ ] DataGrid des factures impayées affiché
- [ ] Colonnes : Étudiant, Montant, Date d'échéance, Actions
- [ ] Données chargées depuis l'API `/api/dashboard/`
- [ ] Total des factures impayées affiché
- [ ] Bouton "Marquer comme payé" fonctionnel (si implémenté)

### 3.5 Dashboard SCOLARITE

#### Affichage
- [ ] Accès à `/dashboard` avec rôle SCOLARITE
- [ ] KPIs affichés :
  - [ ] Total étudiants
  - [ ] Total inscriptions
  - [ ] Inscriptions cette année

### 3.6 Gestion des Erreurs Dashboard
- [ ] Erreur de chargement → Message d'erreur affiché
- [ ] Erreur 401 → Redirection vers login
- [ ] Erreur 403 → Message "Accès refusé"
- [ ] Erreur 500 → Message "Erreur serveur"
- [ ] Loading spinner affiché pendant le chargement

---

## 👥 4. Gestion des Étudiants (`/students`)

### 4.1 Accès et Affichage

#### RECTEUR / ADMIN_SI
- [ ] Accès à `/students` autorisé
- [ ] Liste complète des étudiants affichée
- [ ] DataGrid avec pagination fonctionnelle
- [ ] Colonnes : Matricule, Nom, Email, Programme, Statut Finance, Actions

#### DOYEN / VALIDATOR_ACAD
- [ ] Accès à `/students` autorisé
- [ ] Liste filtrée par faculté (scope)
- [ ] Seuls les étudiants de sa faculté visibles

#### USER_STUDENT
- [ ] Accès à `/students` autorisé
- [ ] Seul son propre profil affiché
- [ ] Card de profil étudiant affichée
- [ ] Informations : Matricule, Email, Programme, Statut Finance, Solde

#### OPERATOR_FINANCE
- [ ] Accès à `/students` autorisé
- [ ] Liste filtrée : étudiants bloqués ou en moratoire
- [ ] Actions de déblocage disponibles

#### SCOLARITE
- [ ] Accès à `/students` autorisé
- [ ] Liste complète des étudiants
- [ ] Bouton "Inscrire un étudiant" visible

### 4.2 Fonctionnalités de Recherche et Filtrage
- [ ] Barre de recherche fonctionnelle (par nom, email, matricule)
- [ ] Filtre par faculté fonctionnel (si applicable)
- [ ] Filtre par statut finance fonctionnel
- [ ] Résultats mis à jour en temps réel

### 4.3 Actions sur les Étudiants

#### Inscription d'un Étudiant (SCOLARITE)
- [ ] Bouton "Inscrire un étudiant" visible
- [ ] Modal d'inscription s'ouvre
- [ ] Formulaire avec champs :
  - [ ] Email (obligatoire)
  - [ ] Matricule permanent (obligatoire)
  - [ ] Date d'entrée (obligatoire)
  - [ ] Programme (obligatoire)
  - [ ] Année académique (obligatoire)
  - [ ] Niveau (obligatoire)
  - [ ] Statut finance (optionnel)
- [ ] Validation côté client
- [ ] Soumission → POST `/api/students/`
- [ ] Toast de succès affiché
- [ ] Liste des étudiants rafraîchie

#### Modification du Statut Finance (OPERATOR_FINANCE)
- [ ] Bouton "Modifier statut" visible pour étudiants bloqués
- [ ] Modal de modification s'ouvre
- [ ] Sélection du nouveau statut (OK, BLOCKED, MORATORIUM)
- [ ] Soumission → PUT `/api/students/{id}/finance-status/`
- [ ] Toast de succès affiché
- [ ] Statut mis à jour dans la liste

#### Validation d'Inscription (VALIDATOR_ACAD / DOYEN)
- [ ] Bouton "Valider inscription" visible
- [ ] Action → POST `/api/registrations/validate/`
- [ ] Toast de succès affiché
- [ ] Statut mis à jour

#### Voir Détails d'un Étudiant
- [ ] Clic sur une ligne → Modal de détails s'ouvre
- [ ] Informations affichées :
  - [ ] Matricule permanent
  - [ ] Email
  - [ ] Programme
  - [ ] Faculté
  - [ ] Statut finance
  - [ ] Solde
  - [ ] Date d'entrée
  - [ ] Inscriptions (liste)
- [ ] Bouton "Fermer" fonctionnel

### 4.4 Gestion des Erreurs
- [ ] Erreur de chargement → Message d'erreur
- [ ] Erreur 403 → Message "Accès refusé"
- [ ] Erreur lors de l'inscription → Toast d'erreur
- [ ] Validation échouée → Toast d'erreur avec détails

---

## 📝 5. Gestion des Notes (`/notes`)

### 5.1 Accès selon les Rôles

#### USER_TEACHER / ENSEIGNANT
- [ ] Accès à `/notes` autorisé
- [ ] Sélecteur de cours affiché (dropdown)
- [ ] Liste des cours chargée depuis `/api/courses/?teacher=me`
- [ ] Premier cours sélectionné par défaut

#### VALIDATOR_ACAD / DOYEN
- [ ] Accès à `/notes` autorisé
- [ ] Vue "PV Jury" affichée
- [ ] Liste des UE avec statut global
- [ ] Bouton "Clôturer le PV" visible

#### USER_STUDENT
- [ ] Accès à `/notes` autorisé
- [ ] Vue read-only affichée
- [ ] Seules ses propres notes visibles
- [ ] DataGrid avec colonnes : Matricule, UE, CC, TP, Exam, Moyenne, Statut

### 5.2 Saisie des Notes (USER_TEACHER)

#### Interface
- [ ] ag-grid éditable affiché
- [ ] Colonnes : Matricule, Étudiant, CC, TP, Exam, Moyenne, Statut
- [ ] Colonnes CC, TP, Exam éditables
- [ ] Colonnes Matricule, Étudiant, Moyenne, Statut non éditables

#### Calcul Automatique de la Moyenne
- [ ] Moyenne calculée automatiquement : `CC * 0.3 + TP * 0.2 + Exam * 0.5`
- [ ] Calcul mis à jour en temps réel lors de la saisie
- [ ] Format avec 2 décimales (ex: 14.50)

#### Sauvegarde
- [ ] Bouton "Enregistrer les notes" visible
- [ ] Clic → POST `/api/grades/bulk-update/`
- [ ] Payload correct : `{ course_id, grades: [{ student_uuid, cc, tp, exam }] }`
- [ ] Toast de succès affiché
- [ ] Données rafraîchies après sauvegarde

### 5.3 PV Jury (VALIDATOR_ACAD)

#### Affichage
- [ ] Liste des UE affichée
- [ ] Statut global pour chaque UE (VALIDÉ / AJOURNÉ)
- [ ] Nombre d'étudiants par UE

#### Clôture du PV
- [ ] Bouton "Clôturer le PV" visible
- [ ] Clic → POST `/api/jury/close/` (alias de `/api/grades/validate/`)
- [ ] Payload : `{ course_id }`
- [ ] Toast de succès affiché
- [ ] Évaluations marquées comme clôturées
- [ ] Registrations pédagogiques mises à jour

### 5.4 Consultation des Notes (USER_STUDENT)

#### Affichage
- [ ] DataGrid read-only affiché
- [ ] Colonnes : Matricule, UE, CC, TP, Exam, Moyenne, Statut
- [ ] Seules les notes de l'étudiant connecté affichées
- [ ] Filtrage par programme si applicable

#### Blocage Financier
- [ ] Si solde < 0 ou statut BLOCKED/MORATORIUM → Message "Accès aux notes bloqué pour raison financière"
- [ ] Notes non affichées

### 5.5 Gestion des Erreurs
- [ ] Erreur de chargement → Toast d'erreur
- [ ] Erreur lors de la sauvegarde → Toast d'erreur avec détails
- [ ] Erreur lors de la clôture → Toast d'erreur
- [ ] Évaluation déjà clôturée → Message d'erreur

---

## 🏛️ 6. Gestion des Facultés (`/faculties`)

### 6.1 Accès et Affichage
- [ ] Accès à `/faculties` autorisé (RECTEUR / ADMIN_SI)
- [ ] Liste des facultés affichée
- [ ] DataGrid avec colonnes : Code, Nom, Tutelle, Statut, Actions

### 6.2 Actions CRUD

#### Création
- [ ] Bouton "Ajouter une faculté" visible
- [ ] Modal de création s'ouvre
- [ ] Formulaire avec champs : Code, Nom, Tutelle, Statut
- [ ] Validation côté client
- [ ] Soumission → POST `/api/faculties/`
- [ ] Toast de succès affiché
- [ ] Liste rafraîchie

#### Modification
- [ ] Bouton "Modifier" visible sur chaque ligne
- [ ] Modal de modification s'ouvre avec données pré-remplies
- [ ] Soumission → PUT `/api/faculties/{id}/`
- [ ] Toast de succès affiché

#### Suppression
- [ ] Bouton "Supprimer" visible (si autorisé)
- [ ] Confirmation demandée
- [ ] Soumission → DELETE `/api/faculties/{id}/`
- [ ] Toast de succès affiché

### 6.3 Gestion des Programmes
- [ ] Liste des programmes par faculté affichée
- [ ] Actions CRUD sur les programmes fonctionnelles

---

## 🔌 7. API Backend - Endpoints

### 7.1 Authentification

#### POST `/api/token/`
- [ ] Endpoint accessible
- [ ] Payload : `{ email, password }`
- [ ] Réponse : `{ token, user, roles }`
- [ ] Erreur 401 si identifiants incorrects

#### POST `/api/auth/regenerate-token/`
- [ ] Endpoint accessible (authentifié)
- [ ] Nouveau token généré
- [ ] Réponse : `{ token }`

### 7.2 Dashboard

#### GET `/api/dashboard/`
- [ ] Endpoint accessible (authentifié)
- [ ] Paramètre `role` ou header `X-Role-Active`
- [ ] Réponse adaptée au rôle :
  - [ ] RECTEUR → `{ kpis, graph }`
  - [ ] USER_TEACHER → `{ courses, stats }`
  - [ ] USER_STUDENT → `{ grades, balance }`
  - [ ] OPERATOR_FINANCE → `{ unpaidInvoices, totalPending }`
  - [ ] SCOLARITE → `{ kpis }`

### 7.3 Étudiants

#### GET `/api/students/`
- [ ] Endpoint accessible (authentifié)
- [ ] Filtrage par rôle actif
- [ ] Pagination fonctionnelle
- [ ] Réponse : `{ results: [...], stats: {...} }`

#### POST `/api/students/`
- [ ] Endpoint accessible (SCOLARITE / OPERATOR_FINANCE)
- [ ] Payload : `{ identity_uuid, matricule_permanent, date_entree, program_id, year_id, level, finance_status }`
- [ ] Validation des champs obligatoires
- [ ] Vérification du solde (blocage si solde > 0)
- [ ] Création de StudentProfile et RegistrationAdmin
- [ ] Réponse : `{ detail, student_id, registration_id }`

#### GET `/api/students/{id}/`
- [ ] Endpoint accessible (authentifié)
- [ ] Détails de l'étudiant avec solde annoté
- [ ] Réponse : `{ id, matricule_permanent, email, program, finance_status, balance, ... }`

#### PUT `/api/students/{id}/finance-status/`
- [ ] Endpoint accessible (OPERATOR_FINANCE)
- [ ] Payload : `{ finance_status }`
- [ ] Mise à jour du statut
- [ ] Réponse : `{ detail }`

### 7.4 Notes

#### GET `/api/grades/`
- [ ] Endpoint accessible (authentifié)
- [ ] Paramètres : `course_id`, `program`
- [ ] Filtrage par rôle :
  - [ ] USER_TEACHER → cours de l'enseignant
  - [ ] USER_STUDENT → notes de l'étudiant
  - [ ] VALIDATOR_ACAD → tous les cours
- [ ] Réponse : `{ results: [{ student_id, matricule_permanent, email, cc, tp, exam, average, status }] }`

#### POST `/api/grades/`
- [ ] Endpoint accessible (USER_TEACHER)
- [ ] Payload : `{ evaluation_id, grades: [{ student_uuid, value }] }`
- [ ] Création/mise à jour des notes
- [ ] Vérification du scope enseignant
- [ ] Réponse : `{ detail, count }`

#### POST `/api/grades/bulk-update/`
- [ ] Endpoint accessible (USER_TEACHER)
- [ ] Payload : `{ course_id, grades: [{ student_uuid, cc, tp, exam }] }`
- [ ] Création/mise à jour des évaluations (CC, TP, Exam) si nécessaire
- [ ] Mise à jour en masse des notes
- [ ] Réponse : `{ detail, count }`

#### POST `/api/grades/validate/` ou `/api/jury/close/`
- [ ] Endpoint accessible (VALIDATOR_ACAD / DOYEN)
- [ ] Payload : `{ course_id }` ou `{ course_ids: [...] }`
- [ ] Calcul des moyennes UE
- [ ] Mise à jour des RegistrationPedagogical
- [ ] Marquage des évaluations comme clôturées
- [ ] Réponse : `{ detail, processed }`

### 7.5 Cours

#### GET `/api/courses/`
- [ ] Endpoint accessible (USER_TEACHER)
- [ ] Paramètre `teacher=me` pour filtrer les cours de l'enseignant
- [ ] Réponse : `{ results: [{ id, code, name, program_code }] }`

### 7.6 Inscriptions

#### POST `/api/registrations/validate/`
- [ ] Endpoint accessible (VALIDATOR_ACAD / DOYEN)
- [ ] Payload : `{ registration_ids: [...], finance_status }`
- [ ] Validation en masse
- [ ] Vérification SoD (pas de validation de soi-même)
- [ ] Vérification du scope (faculté)
- [ ] Réponse : `{ detail, validated_count, errors }`

### 7.7 Workflows

#### POST `/api/workflows/`
- [ ] Endpoint accessible (selon workflow)
- [ ] Payload : `{ workflow, registration_id }`
- [ ] Workflows supportés :
  - [ ] `JURY_VALIDATION` (VALIDATOR_ACAD / DOYEN)
  - [ ] `CERTIFICATE_ISSUE` (SCOLARITE)
- [ ] Vérification SoD
- [ ] Réponse : `{ detail }`

### 7.8 Facultés et Programmes

#### GET `/api/faculties/`
- [ ] Endpoint accessible (authentifié)
- [ ] Liste des facultés
- [ ] Filtrage par scope si applicable

#### POST `/api/faculties/`
- [ ] Endpoint accessible (RECTEUR / ADMIN_SI)
- [ ] Création d'une faculté

#### GET `/api/programs/`
- [ ] Endpoint accessible (authentifié)
- [ ] Liste des programmes
- [ ] Filtrage par faculté si applicable

---

## 🔒 8. Sécurité et Permissions

### 8.1 RBAC (Role-Based Access Control)
- [ ] Chaque endpoint vérifie le rôle actif
- [ ] Accès refusé (403) si rôle non autorisé
- [ ] Header `X-Role-Active` requis pour les endpoints protégés

### 8.2 SoD (Separation of Duties)
- [ ] Validation de soi-même bloquée (SoD violation)
- [ ] Log d'audit créé pour les violations SoD
- [ ] Message d'erreur clair affiché

### 8.3 Scope Filtering
- [ ] DOYEN voit uniquement sa faculté
- [ ] USER_TEACHER voit uniquement ses cours
- [ ] USER_STUDENT voit uniquement ses données

### 8.4 Audit Trail
- [ ] Actions sensibles loggées dans SysAuditLog
- [ ] Rôle actif enregistré dans les logs
- [ ] Email de l'acteur enregistré

---

## 🎨 9. Interface Utilisateur

### 9.1 Navigation
- [ ] AppBar visible sur toutes les pages (si connecté)
- [ ] Logo/titre "IUEC ERP" affiché
- [ ] Email de l'utilisateur affiché
- [ ] Sélecteur de rôle fonctionnel
- [ ] Toggle dark mode fonctionnel
- [ ] Bouton déconnexion fonctionnel

### 9.2 Thème et Design
- [ ] Thème clair/sombre fonctionnel
- [ ] Persistance du thème dans localStorage
- [ ] Pas de flash au rechargement
- [ ] Design cohérent sur toutes les pages
- [ ] Responsive (mobile, tablette, desktop)

### 9.3 Notifications
- [ ] Toast de succès affichés (vert)
- [ ] Toast d'erreur affichés (rouge)
- [ ] Toast d'information affichés (bleu)
- [ ] Position : top-right
- [ ] Auto-dismiss après quelques secondes

### 9.4 Loading States
- [ ] Spinner affiché pendant les chargements
- [ ] Skeleton loaders si applicable
- [ ] Pas de contenu vide pendant le chargement

### 9.5 Gestion des Erreurs UI
- [ ] Messages d'erreur clairs et compréhensibles
- [ ] Codes d'erreur HTTP affichés si pertinent
- [ ] Suggestions de solutions si applicable

---

## 🔄 10. Workflows Métier

### 10.1 Workflow d'Inscription Étudiant
1. [ ] SCOLARITE crée une inscription
2. [ ] Étudiant créé avec statut finance OK
3. [ ] RegistrationAdmin créée
4. [ ] VALIDATOR_ACAD valide l'inscription
5. [ ] Statut finance mis à jour
6. [ ] Étudiant peut accéder à ses notes

### 10.2 Workflow de Saisie des Notes
1. [ ] USER_TEACHER sélectionne un cours
2. [ ] Liste des étudiants chargée
3. [ ] Saisie des notes (CC, TP, Exam)
4. [ ] Calcul automatique de la moyenne
5. [ ] Sauvegarde en masse
6. [ ] Notes enregistrées dans la base

### 10.3 Workflow de Validation des Notes (PV Jury)
1. [ ] VALIDATOR_ACAD accède à `/notes`
2. [ ] Vue PV Jury affichée
3. [ ] Liste des UE avec statuts
4. [ ] Clôture du PV
5. [ ] Calcul des moyennes UE
6. [ ] Mise à jour des RegistrationPedagogical
7. [ ] Évaluations marquées comme clôturées

### 10.4 Workflow de Blocage Financier
1. [ ] OPERATOR_FINANCE bloque un étudiant
2. [ ] Statut finance → BLOCKED
3. [ ] Étudiant ne peut plus accéder à ses notes
4. [ ] Message d'erreur affiché
5. [ ] OPERATOR_FINANCE débloque l'étudiant
6. [ ] Accès aux notes restauré

---

## 🐛 11. Tests d'Erreurs et Cas Limites

### 11.1 Erreurs Réseau
- [ ] Perte de connexion → Message d'erreur
- [ ] Timeout → Message d'erreur
- [ ] Retry automatique si applicable

### 11.2 Erreurs Serveur
- [ ] Erreur 500 → Message "Erreur serveur"
- [ ] Erreur 503 → Message "Service indisponible"
- [ ] Logs d'erreur dans la console backend

### 11.3 Données Manquantes
- [ ] Liste vide → Message "Aucune donnée"
- [ ] Champs optionnels gérés correctement
- [ ] Pas de crash si données null/undefined

### 11.4 Validation des Données
- [ ] Champs obligatoires validés côté client
- [ ] Formats de données validés (email, date, etc.)
- [ ] Messages d'erreur de validation clairs

### 11.5 Cas Limites
- [ ] Très grand nombre d'étudiants → Pagination fonctionnelle
- [ ] Notes avec valeurs extrêmes (0, 20, négatif, > 20)
- [ ] Changement de rôle pendant une action
- [ ] Token expiré → Redirection vers login

---

## 📝 12. Observations et Améliorations

### 12.1 Erreurs Identifiées

**Erreur 1 :**
- Description : 
- Fichier/Endpoint concerné :
- Étapes pour reproduire :
- Impact :

**Erreur 2 :**
- Description :
- Fichier/Endpoint concerné :
- Étapes pour reproduire :
- Impact :

### 12.2 Améliorations Suggérées

**Amélioration 1 :**
- Description :
- Priorité : Haute / Moyenne / Basse
- Bénéfice :

**Amélioration 2 :**
- Description :
- Priorité : Haute / Moyenne / Basse
- Bénéfice :

### 12.3 Bugs Mineurs

- [ ] Bug 1 :
- [ ] Bug 2 :
- [ ] Bug 3 :

### 12.4 Suggestions UX/UI

- [ ] Suggestion 1 :
- [ ] Suggestion 2 :
- [ ] Suggestion 3 :

---

## ✅ 13. Résumé du Test

### Statistiques
- **Total de tests :** ________
- **Tests réussis :** ________
- **Tests échoués :** ________
- **Tests partiels :** ________
- **Taux de réussite :** ________%

### Fonctionnalités Critiques
- [ ] Authentification fonctionnelle
- [ ] Gestion des rôles fonctionnelle
- [ ] Dashboard adaptatif fonctionnel
- [ ] Gestion des étudiants fonctionnelle
- [ ] Gestion des notes fonctionnelle
- [ ] API backend fonctionnelle
- [ ] Sécurité et permissions respectées

### Conclusion
**Date de fin de test :** _______________  
**Testeur :** _______________  
**Version testée :** _______________

**Commentaires généraux :**




---

## 📞 Support

Pour toute question ou problème, contactez l'équipe de développement.

**Document créé le :** _______________  
**Dernière mise à jour :** _______________
