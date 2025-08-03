# Déploiement sur Vercel - Discord Server Backup Tool

## Étapes pour déployer sur Vercel

### 1. Prérequis
- Compte Vercel (https://vercel.com)
- Git repository de votre projet

### 2. Configuration des variables d'environnement
Dans votre dashboard Vercel, ajoutez ces variables d'environnement :
- `SESSION_SECRET` : Clé secrète pour les sessions Flask (générez une chaîne aléatoire)

### 3. Déploiement
1. Connectez votre repository Git à Vercel
2. Vercel détectera automatiquement le projet Python
3. Le fichier `vercel.json` configure le déploiement
4. L'application sera accessible via l'URL fournie par Vercel

### 4. Structure des fichiers pour Vercel
- `api/index.py` : Point d'entrée pour Vercel
- `vercel.json` : Configuration de déploiement
- `requirements-vercel.txt` : Dépendances Python
- `.vercelignore` : Fichiers à ignorer lors du déploiement

### 5. Fonctionnalités disponibles
- Interface web pour copier des serveurs Discord
- Sauvegarde et restauration de structures de serveurs
- Support des tokens Discord utilisateur

### Note importante
⚠️ Les tokens Discord sont sensibles - ne les partagez jamais et utilisez-les de manière responsable.