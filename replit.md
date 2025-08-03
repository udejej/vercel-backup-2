# Discord Server Backup Tool - Project Documentation

## Project Overview
Application Flask pour sauvegarder et restaurer la structure des serveurs Discord (canaux, rôles, emojis, stickers).

## Architecture
- **main.py**: Application Flask web avec interface utilisateur
- **backup_discord.py**: Interface ligne de commande
- **discord_bot.py**: Interface bot Discord
- **discord_api.py**: Client API Discord avec gestion des limites de taux
- **backup_utils.py**: Utilitaires pour sauvegarder/charger les données
- **templates/**: Templates HTML pour l'interface web

## Stack Technique
- Python 3.11+
- Flask (serveur web)
- discord.py (API Discord)
- aiohttp (requêtes HTTP asynchrones)
- Gunicorn (serveur WSGI)

## Configuration Vercel
- Migration en cours vers Vercel
- Nécessite adaptations pour la plateforme serverless

## User Preferences
- Langue: Français
- Interface: Web prioritaire

## Recent Changes
- 2025-08-02: ✓ Migration Vercel préparée - Fichiers de configuration créés
- 2025-08-02: ✓ Structure API adaptée pour serverless Vercel
- 2025-08-02: ✓ Configuration runtime et dépendances finalisées
- 2025-08-02: ✓ Design moderne appliqué - Arrière-plan gradiant et cartes en verre
- 2025-08-02: ✓ Interface modernisée avec animations et icônes Font Awesome
- 2025-08-02: ⚠️ Problème synchronisation Vercel - Design ne s'affiche pas sur site déployé

## Fichiers Vercel
- `vercel.json` : Configuration de déploiement
- `api/index.py` : Point d'entrée Flask pour Vercel
- `api/requirements.txt` : Dépendances Python
- `runtime.txt` : Version Python 3.11
- `.vercelignore` : Fichiers à exclure du déploiement
- `README-VERCEL.md` : Instructions de déploiement