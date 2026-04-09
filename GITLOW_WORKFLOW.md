# Workflow Gitlow

Ce projet suit le workflow Gitlow, dérivé du Gitflow et ajusté pour rester léger mais structuré au quotidien. L'objectif est de garantir que les branches principales restent simples, que les tests d'intégration s'exécutent dans `develop`, et que les correctifs urgents peuvent être poussés rapidement en production.

## Branches clés
- **`main`** : Contient uniquement du code prêt pour la production. Chaque commit sur `main` doit correspondre à une version testée et déployable.
- **`develop`** : Branche d'intégration. Toutes les fonctionnalités fusionnées en `develop` ont été testées de manière isolée, et `develop` est la base pour les futurs `release`.
- **`feature/*`** : Nouvelles fonctionnalités ou travaux exploratoires. Chaque fonctionnalité commence par `feature/` et est fusionnée dans `develop` via une PR une fois prête.
- **`release/*`** : Prépare une nouvelle version. On crée une branche `release/vX.Y` à partir de `develop`, on stabilise, corrige les bugs restants et on fusionne ensuite à la fois dans `main` (pour la release) et dans `develop` (pour récupérer les correctifs éventuels).
- **`hotfix/*`** : Correctifs urgents sur `main`. Après correction, on fusionne dans `main` et dans `develop` pour que le correctif soit propagé.

## Processus quotidien
1. Créer une branche `feature/` à partir de `develop` pour chaque tâche. Les tâches légères peuvent être taguées par issue dans le titre.
2. Valider localement + exécuter les tests unitaires, puis ouvrir une PR vers `develop`. Identifier clairement l'état (Draft/Ready) et les dépendances.
3. `develop` est régulièrement intégré via une branche `release/` dès qu'une version stable est prête. Lancer le pipeline de tests complet sur la branche `release/` avant d'approuver.
4. Fusionner la branche `release/` dans `main` (déploiement) et dans `develop` (retour des corrections). Tagger la version sur `main`.
5. Pour un correctif urgent, partir de `main` avec une branche `hotfix/`; tester, puis fusionner dans `main` et `develop` avant de déployer immédiatement.

## Commandes recommandées
- `git checkout develop` → `git pull` pour démarrer un nouveau travail.
- `git checkout -b feature/ma-tache` puis `git push -u origin feature/ma-tache`.
- Créer une PR vers `develop` et mentionner le ou les tests automatisés associés.
- Pour une release : `git checkout -b release/vX.Y develop`, corriger, puis `git merge --no-ff release/vX.Y` dans `main` et `develop`.
- Pour un hotfix : `git checkout -b hotfix/description main`, puis fusionner dans `main` et `develop`.

## Règles de fusion
1. Les PR vers `develop` exigent au moins un reviewer et un pipeline vert.
2. `main` n'accepte que les merges de `release/*` ou `hotfix/*` validés.
3. Lors d'un hotfix, documenter l'urgence et les tests exécutés. Si nécessaire, créer un ticket post-déploiement pour atteindre la couverture test.

## Vérifications
- Toujours exécuter les tests unitaires et d'intégration avant de fusionner.
- Réconcilier les dépendances (backend/frontend) dans `develop` avant une release.
- Vérifier les fichiers de configuration (`docker-compose`, `render.yaml`) pour tout changement critique.
