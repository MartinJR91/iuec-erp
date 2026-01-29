# 🔐 Identifiants de Test - IUEC-ERP

## Utilisateurs Disponibles

### 1. Recteur (Multi-rôles)
- **Email** : `recteur@iuec.cm`
- **Mot de passe** : `recteur123!`
- **Rôles** : RECTEUR, USER_TEACHER, VIEWER_STRATEGIC
- **Accès** : Dashboard institutionnel complet, gestion facultés/étudiants

### 2. Doyen FASE
- **Email** : `doyen@iuec.cm`
- **Mot de passe** : `doyen123!`
- **Rôles** : DOYEN, VALIDATOR_ACAD
- **Scope** : FASE (Faculté des Sciences Économiques)
- **Accès** : Dashboard académique, gestion étudiants de sa faculté, validation inscriptions

### 3. Enseignant
- **Email** : `marie.dupont@iuec.cm`
- **Mot de passe** : `ens123!`
- **Rôles** : USER_TEACHER
- **Accès** : Dashboard enseignant, saisie notes

### 4. Étudiant
- **Email** : `elise.ngono@iuec.cm`
- **Mot de passe** : `etu123!`
- **Rôles** : USER_STUDENT
- **Accès** : Dashboard étudiant, consultation notes, solde

### 5. Opérateur Finance
- **Email** : `finance@iuec.cm`
- **Mot de passe** : `fin123!`
- **Rôles** : OPERATOR_FINANCE
- **Accès** : Dashboard finance, gestion factures, déblocage étudiants

### 6. Scolarité
- **Email** : `scolarite@iuec.cm`
- **Mot de passe** : `scol123!`
- **Rôles** : SCOLARITE
- **Accès** : Dashboard scolarité, inscription/gestion étudiants

### 7. Admin SI
- **Email** : `admin@iuec.cm`
- **Mot de passe** : `admin123!`
- **Rôles** : RECTEUR, USER_TEACHER, VIEWER_STRATEGIC (superuser)
- **Accès** : Tous les accès (superuser Django)

---

## 🧪 Tests Recommandés

### Test 1 : Dashboard RECTEUR
1. Se connecter avec `recteur@iuec.cm` / `recteur123!`
2. Vérifier l'affichage des KPI
3. Vérifier les boutons "Gérer les facultés" et "Gérer les étudiants"
4. Vérifier le graphique d'évolution

### Test 2 : Dashboard DOYEN
1. Se connecter avec `doyen@iuec.cm` / `doyen123!`
2. Vérifier l'affichage du dashboard académique
3. Vérifier le bouton "Gérer les étudiants"
4. Vérifier que seuls les étudiants de FASE sont visibles

### Test 3 : Changement de Rôle
1. Se connecter avec `recteur@iuec.cm`
2. Utiliser le sélecteur de rôle dans l'AppBar
3. Changer vers USER_TEACHER
4. Vérifier que le dashboard s'adapte

### Test 4 : Gestion Étudiants
1. Se connecter avec `recteur@iuec.cm`
2. Aller sur `/students`
3. Vérifier la liste complète des étudiants
4. Tester la recherche et la pagination

### Test 5 : Dashboard SCOLARITE
1. Se connecter avec `scolarite@iuec.cm` / `scol123!`
2. Vérifier l'affichage du dashboard "Gestion de la scolarité"
3. Vérifier le bouton "Inscrire / Gérer étudiants"
4. Aller sur `/students` et vérifier l'accès complet

### Test 6 : Dark Mode
1. Se connecter avec n'importe quel utilisateur
2. Cliquer sur le toggle dark mode
3. Vérifier le changement de thème
4. Recharger la page → vérifier la persistance

---

## ⚠️ Notes Importantes

- Tous les mots de passe sont en clair pour les tests
- Les utilisateurs sont créés via `seed_demo_users()`
- Pour réinitialiser : exécuter `python manage.py shell -c "from identity.seed import seed_demo_users; seed_demo_users()"`
- Les rôles sont liés via `IdentityRoleLink`
- Le scope du DOYEN est défini dans `metadata.scope_by_role`

---

**Dernière mise à jour** : 2026-01-29
