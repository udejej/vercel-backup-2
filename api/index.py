from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import asyncio
import json
import logging
import threading

from discord_api import DiscordAPI

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        token = request.form.get('token')
        source_server_id = request.form.get('source_server_id')
        target_server_id = request.form.get('target_server_id')
        
        # Vérifier que toutes les informations nécessaires sont présentes
        if not token or not source_server_id or not target_server_id:
            flash('Veuillez remplir tous les champs (token, ID du serveur source et ID du serveur cible).', 'danger')
            return redirect(url_for('index'))
        
        # Vérifier que les serveurs source et cible sont différents
        if source_server_id == target_server_id:
            flash('Les IDs des serveurs source et cible doivent être différents.', 'danger')
            return redirect(url_for('index'))
        
        # Version Vercel - Test rapide seulement (limitation 10 secondes)
        try:
            result = asyncio.run(asyncio.wait_for(
                validate_servers_quick(token, source_server_id, target_server_id),
                timeout=8  # 8 secondes max pour Vercel
            ))
            
            if result['success']:
                flash(f"✅ Serveurs validés: {result['source_name']} → {result['target_name']}", 'success')
                flash("⚠️ Pour la copie complète, utilisez Replit (limitations de temps Vercel)", 'warning')
            else:
                flash(f"❌ Erreur: {result['message']}", 'danger')
                
        except asyncio.TimeoutError:
            flash("⏱️ Validation timeout sur Vercel. Utilisez Replit pour les opérations complètes.", 'warning')
        except Exception as e:
            flash(f"❌ Erreur: {str(e)}", 'danger')
        
        return redirect(url_for('index'))
    
    # Vérifier s'il y a un résultat de copie à afficher
    if 'copy_result' in session:
        result = session.pop('copy_result')
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
    
    return render_template('index.html')

async def validate_servers_quick(token, source_server_id, target_server_id):
    """Validation rapide pour Vercel (< 8 secondes)"""
    discord_api = DiscordAPI(token)
    
    try:
        # Test rapide des serveurs uniquement
        source_server = await discord_api.get_server(source_server_id)
        if not source_server:
            return {'success': False, 'message': f'Serveur source inaccessible (ID: {source_server_id})'}
        
        target_server = await discord_api.get_server(target_server_id)
        if not target_server:
            return {'success': False, 'message': f'Serveur cible inaccessible (ID: {target_server_id})'}
        
        await discord_api.close()
        
        return {
            'success': True,
            'source_name': source_server.get('name', 'Unknown'),
            'target_name': target_server.get('name', 'Unknown')
        }
    
    except Exception as e:
        await discord_api.close()
        return {'success': False, 'message': str(e)}

async def copy_server(token, source_server_id, target_server_id):
    """
    Copie un serveur Discord vers un autre serveur.
    
    Args:
        token: Le token Discord de l'utilisateur
        source_server_id: L'ID du serveur à copier
        target_server_id: L'ID du serveur où copier la structure
        
    Returns:
        Tuple (success, message): Un booléen indiquant si la copie a réussi et un message
    """
    discord_api = DiscordAPI(token)
    
    try:
        # Étape 1: Vérifier que les serveurs source et cible existent
        logger.info(f"Vérification du serveur source ID: {source_server_id}")
        source_server = await discord_api.get_server(source_server_id)
        if not source_server:
            return False, f"Impossible d'accéder au serveur source (ID: {source_server_id}). Vérifiez l'ID et vos permissions."
        
        logger.info(f"Vérification du serveur cible ID: {target_server_id}")
        target_server = await discord_api.get_server(target_server_id)
        if not target_server:
            return False, f"Impossible d'accéder au serveur cible (ID: {target_server_id}). Vérifiez l'ID et vos permissions."
        
        # Étape 2: Extraire les données du serveur source
        source_name = source_server.get('name', 'Unknown')
        logger.info(f"Extraction des données du serveur source: {source_name}")
        
        logger.info("Récupération des canaux...")
        channels = await discord_api.get_channels(source_server_id)
        # Ajout d'une pause pour éviter les rate limits
        await asyncio.sleep(1)
        
        logger.info("Récupération des rôles...")
        roles = await discord_api.get_roles(source_server_id)
        await asyncio.sleep(1)
        
        logger.info("Récupération des emojis...")
        emojis = await discord_api.get_emojis(source_server_id)
        await asyncio.sleep(1)
        
        logger.info("Récupération des stickers...")
        stickers = await discord_api.get_stickers(source_server_id)
        await asyncio.sleep(1)
        
        # Étape 3: Nettoyer le serveur cible
        target_name = target_server.get('name', 'Unknown')
        logger.info(f"Nettoyage du serveur cible: {target_name}")
        
        # Ajoutons un bloc try/except spécifique pour le nettoyage du serveur
        try:
            await discord_api.clear_server(target_server_id)
            await asyncio.sleep(2)  # Pause plus longue après le nettoyage
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du serveur: {str(e)}")
            return False, f"Erreur lors du nettoyage du serveur cible: {str(e)}"
        
        # Étape 4: Restaurer la structure du serveur cible
        # D'abord les rôles pour conserver les permissions
        logger.info("Création des rôles...")
        role_id_map = {}
        if roles:
            role_id_map = await discord_api.restore_roles(target_server_id, roles)
        
        # Ensuite les canaux et catégories
        logger.info("Création des canaux...")
        if channels:
            await discord_api.restore_channels(target_server_id, channels, role_id_map)
        
        # Finalement les emojis et stickers
        logger.info("Ajout des emojis...")
        if emojis:
            await discord_api.restore_emojis(target_server_id, emojis)
        
        logger.info("Ajout des stickers...")
        if stickers:
            await discord_api.restore_stickers(target_server_id, stickers)
        
        logger.info(f"Copie terminée avec succès ! Le serveur '{source_name}' a été copié vers '{target_name}'.")
        
        return True, f"Le serveur '{source_name}' a été copié avec succès vers '{target_name}'!"
        
    except Exception as e:
        logger.error(f"Erreur générale pendant la copie: {str(e)}")
        return False, f"Une erreur s'est produite: {str(e)}"
    
    finally:
        # Fermer la session aiohttp
        await discord_api.close()

if __name__ == '__main__':
    app.run(debug=True)
