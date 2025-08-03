from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import asyncio
import json
import logging

from discord_api import DiscordAPI

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
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
        
        # Démarrer le processus de copie en arrière-plan dans un thread
        # pour éviter les timeouts du serveur web
        import threading
        
        def run_copy_async():
            try:
                # Créer une nouvelle boucle d'événements pour ce thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Configurer un délai d'attente plus long (5 minutes)
                result, message = loop.run_until_complete(
                    asyncio.wait_for(
                        copy_server(token, source_server_id, target_server_id),
                        timeout=300  # 5 minutes max
                    )
                )
                loop.close()
                
                # Stocker le résultat dans la session pour l'afficher à l'utilisateur lors du prochain chargement de page
                if result:
                    session['copy_result'] = {'success': True, 'message': 'Serveur copié avec succès!'}
                else:
                    session['copy_result'] = {'success': False, 'message': f'Erreur: {message}'}
                
            except Exception as e:
                logger.error(f"Erreur pendant la copie: {str(e)}")
                session['copy_result'] = {'success': False, 'message': f'Une erreur est survenue: {str(e)}'}
        
        # Informer l'utilisateur que la copie a commencé
        flash('Copie du serveur Discord en cours... Cette opération peut prendre plusieurs minutes. Vous pouvez actualiser cette page pour voir le statut.', 'info')
        
        # Lancer le processus en arrière-plan
        thread = threading.Thread(target=run_copy_async)
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('index'))
    
    # Vérifier s'il y a un résultat de copie à afficher
    if 'copy_result' in session:
        result = session.pop('copy_result')
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
    
    return render_template('index.html')

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
        try:
            role_id_map = await discord_api.restore_roles(target_server_id, roles)
            await asyncio.sleep(2)  # Pause après la création des rôles
        except Exception as e:
            logger.error(f"Erreur lors de la création des rôles: {str(e)}")
            return False, f"Erreur lors de la création des rôles: {str(e)}"
        
        # Ensuite les canaux
        logger.info("Création des canaux...")
        try:
            await discord_api.restore_channels(target_server_id, channels, role_id_map)
            await asyncio.sleep(2)  # Pause après la création des canaux
        except Exception as e:
            logger.error(f"Erreur lors de la création des canaux: {str(e)}")
            return False, f"Erreur lors de la création des canaux: {str(e)}"
        
        # Puis les émojis et stickers
        logger.info("Création des émojis...")
        try:
            await discord_api.restore_emojis(target_server_id, emojis)
            await asyncio.sleep(2)  # Pause après la création des émojis
        except Exception as e:
            logger.error(f"Erreur lors de la création des émojis: {str(e)}")
            # On continue même si les émojis échouent
        
        logger.info("Création des stickers...")
        try:
            await discord_api.restore_stickers(target_server_id, stickers)
        except Exception as e:
            logger.error(f"Erreur lors de la création des stickers: {str(e)}")
            # On continue même si les stickers échouent
        
        logger.info(f"Copie du serveur terminée avec succès! Serveur '{source_name}' copié vers '{target_name}'")
        return True, f"Copie réussie! Serveur '{source_name}' copié vers '{target_name}'"
        
    except Exception as e:
        logger.error(f"Erreur pendant la copie du serveur: {str(e)}")
        return False, f"Erreur pendant la copie: {str(e)}"
    
    finally:
        # S'assurer que la session est fermée
        try:
            await discord_api.close()
        except:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)