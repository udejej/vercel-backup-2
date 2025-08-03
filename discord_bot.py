#!/usr/bin/env python3
"""
Bot Discord pour copier des serveurs
Ce bot permet de copier un serveur Discord vers un autre serveur en utilisant des commandes.
"""

import os
import discord
import asyncio
import logging
from discord.ext import commands
from discord_api import DiscordAPI
from typing import Dict, Optional, List

# Configuration des logs
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Créer un bot avec les intents nécessaires
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionnaire pour stocker les tokens et les travaux en cours
user_tokens = {}
copy_tasks = {}

@bot.event
async def on_ready():
    """Événement déclenché lorsque le bot est prêt."""
    logger.info(f'Bot connecté en tant que {bot.user.name}')
    logger.info(f'ID du bot: {bot.user.id}')
    logger.info('------')
    
    # Définir le statut du bot
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="!aide pour les commandes"
    ))

@bot.command(name='aide')
async def help_command(ctx):
    """Affiche l'aide des commandes disponibles."""
    embed = discord.Embed(
        title="Aide - Bot Copieur de Serveur Discord",
        description="Ce bot vous permet de copier un serveur Discord vers un autre serveur.",
        color=0x00AAFF
    )
    
    embed.add_field(
        name="!settoken <token>",
        value="Définir votre token Discord d'utilisateur (à envoyer en DM uniquement pour la sécurité)",
        inline=False
    )
    
    embed.add_field(
        name="!copy <id_source> <id_cible>",
        value="Copier un serveur source vers un serveur cible",
        inline=False
    )
    
    embed.add_field(
        name="!status",
        value="Vérifier le statut du processus de copie en cours",
        inline=False
    )
    
    embed.add_field(
        name="!cleartoken",
        value="Supprimer votre token stocké (à envoyer en DM uniquement)",
        inline=False
    )
    
    embed.set_footer(text="⚠️ N'utilisez jamais la commande !settoken dans un canal public!")
    
    await ctx.send(embed=embed)

@bot.command(name='settoken')
async def set_token(ctx, token: str):
    """Définir le token Discord de l'utilisateur."""
    # Vérifier si la commande est utilisée en DM pour la sécurité
    if not isinstance(ctx.channel, discord.DMChannel):
        # Si la commande est utilisée dans un canal public, supprimer immédiatement le message
        try:
            await ctx.message.delete()
        except:
            pass
        
        # Avertir l'utilisateur
        warning = await ctx.send("⚠️ Pour des raisons de sécurité, utilisez la commande `!settoken` uniquement en message privé!")
        await asyncio.sleep(5)
        await warning.delete()
        return
    
    # Stocker le token
    user_tokens[ctx.author.id] = token
    await ctx.send("✅ Votre token a été configuré avec succès. Vous pouvez maintenant utiliser `!copy` pour copier un serveur.")

@bot.command(name='cleartoken')
async def clear_token(ctx):
    """Supprimer le token Discord stocké pour l'utilisateur."""
    # Vérifier si la commande est utilisée en DM pour la sécurité
    if not isinstance(ctx.channel, discord.DMChannel):
        # Si la commande est utilisée dans un canal public, supprimer le message
        try:
            await ctx.message.delete()
        except:
            pass
        
        # Avertir l'utilisateur
        warning = await ctx.send("⚠️ Pour des raisons de sécurité, utilisez la commande `!cleartoken` uniquement en message privé!")
        await asyncio.sleep(5)
        await warning.delete()
        return
    
    # Supprimer le token s'il existe
    if ctx.author.id in user_tokens:
        del user_tokens[ctx.author.id]
        await ctx.send("✅ Votre token a été supprimé avec succès.")
    else:
        await ctx.send("❌ Aucun token n'était stocké pour vous.")

@bot.command(name='copy')
async def copy_server(ctx, source_id: str, target_id: str):
    """Copier un serveur Discord vers un autre serveur."""
    # Vérifier si l'utilisateur a défini un token
    if ctx.author.id not in user_tokens:
        await ctx.send("❌ Vous devez d'abord définir votre token avec la commande `!settoken <token>` en message privé.")
        return
    
    # Vérifier si l'utilisateur a déjà une tâche de copie en cours
    if ctx.author.id in copy_tasks and not copy_tasks[ctx.author.id].done():
        await ctx.send("⚠️ Vous avez déjà une copie de serveur en cours. Utilisez `!status` pour vérifier son état.")
        return
    
    # Vérifier que les serveurs source et cible sont différents
    if source_id == target_id:
        await ctx.send("❌ Les IDs des serveurs source et cible doivent être différents.")
        return
    
    # Envoyer un message de confirmation
    message = await ctx.send("🔄 Démarrage de la copie du serveur... Cela peut prendre plusieurs minutes.")
    
    # Créer une tâche asyncio pour effectuer la copie en arrière-plan
    task = asyncio.create_task(perform_copy(ctx, user_tokens[ctx.author.id], source_id, target_id, message))
    copy_tasks[ctx.author.id] = task
    
    # Attacher une fonction de callback à la tâche pour gérer les erreurs
    task.add_done_callback(lambda t: handle_copy_completion(t, ctx))

@bot.command(name='status')
async def check_status(ctx):
    """Vérifier le statut de la tâche de copie en cours."""
    if ctx.author.id not in copy_tasks:
        await ctx.send("❌ Vous n'avez aucune tâche de copie en cours ou récente.")
        return
    
    task = copy_tasks[ctx.author.id]
    
    if task.done():
        if task.exception():
            await ctx.send("❌ Votre dernière tâche de copie a échoué avec l'erreur suivante :\n```\n" + 
                           str(task.exception()) + "\n```")
        else:
            result = task.result()
            if result.get('success'):
                await ctx.send("✅ Votre dernière tâche de copie s'est terminée avec succès.")
            else:
                await ctx.send("❌ Votre dernière tâche de copie a échoué :\n" + result.get('message', 'Erreur inconnue'))
    else:
        await ctx.send("🔄 Une copie de serveur est en cours. Cela peut prendre plusieurs minutes.")

async def perform_copy(ctx, token, source_id, target_id, message) -> Dict:
    """
    Effectue la copie du serveur en arrière-plan.
    
    Args:
        ctx: Le contexte de la commande Discord
        token: Le token Discord de l'utilisateur
        source_id: L'ID du serveur source
        target_id: L'ID du serveur cible
        message: Le message à mettre à jour pendant le processus
        
    Returns:
        Un dictionnaire contenant le résultat de l'opération
    """
    # Initialiser l'API Discord
    discord_api = DiscordAPI(token)
    
    try:
        # Étape 1: Vérifier les serveurs source et cible
        await message.edit(content="🔄 Vérification des serveurs...")
        
        source_server = await discord_api.get_server(source_id)
        if not source_server:
            return {'success': False, 'message': f"❌ Impossible d'accéder au serveur source (ID: {source_id}). Vérifiez l'ID et vos permissions."}
        
        target_server = await discord_api.get_server(target_id)
        if not target_server:
            return {'success': False, 'message': f"❌ Impossible d'accéder au serveur cible (ID: {target_id}). Vérifiez l'ID et vos permissions."}
        
        # Étape 2: Extraire les données du serveur source
        source_name = source_server.get('name', 'Unknown')
        target_name = target_server.get('name', 'Unknown')
        
        await message.edit(content=f"🔄 Extraction des données du serveur source: {source_name}...")
        
        # Récupérer les canaux
        await message.edit(content=f"🔄 Récupération des canaux de {source_name}...")
        channels = await discord_api.get_channels(source_id)
        await asyncio.sleep(1)
        
        # Récupérer les rôles
        await message.edit(content=f"🔄 Récupération des rôles de {source_name}...")
        roles = await discord_api.get_roles(source_id)
        await asyncio.sleep(1)
        
        # Récupérer les emojis
        await message.edit(content=f"🔄 Récupération des emojis de {source_name}...")
        emojis = await discord_api.get_emojis(source_id)
        await asyncio.sleep(1)
        
        # Récupérer les stickers
        await message.edit(content=f"🔄 Récupération des stickers de {source_name}...")
        stickers = await discord_api.get_stickers(source_id)
        await asyncio.sleep(1)
        
        # Étape 3: Nettoyer le serveur cible
        await message.edit(content=f"⚠️ Nettoyage du serveur cible: {target_name}...")
        
        try:
            await discord_api.clear_server(target_id)
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du serveur: {str(e)}")
            return {'success': False, 'message': f"❌ Erreur lors du nettoyage du serveur cible: {str(e)}"}
        
        # Étape 4: Restaurer la structure sur le serveur cible
        # Créer les rôles
        await message.edit(content=f"🔄 Création des rôles sur {target_name}...")
        try:
            role_id_map = await discord_api.restore_roles(target_id, roles)
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Erreur lors de la création des rôles: {str(e)}")
            return {'success': False, 'message': f"❌ Erreur lors de la création des rôles: {str(e)}"}
        
        # Créer les canaux
        await message.edit(content=f"🔄 Création des canaux sur {target_name}...")
        try:
            await discord_api.restore_channels(target_id, channels, role_id_map)
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Erreur lors de la création des canaux: {str(e)}")
            return {'success': False, 'message': f"❌ Erreur lors de la création des canaux: {str(e)}"}
        
        # Créer les emojis
        await message.edit(content=f"🔄 Création des emojis sur {target_name}...")
        try:
            await discord_api.restore_emojis(target_id, emojis)
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Erreur lors de la création des emojis: {str(e)}")
            # On continue même si les emojis échouent
        
        # Créer les stickers
        await message.edit(content=f"🔄 Création des stickers sur {target_name}...")
        try:
            await discord_api.restore_stickers(target_id, stickers)
        except Exception as e:
            logger.error(f"Erreur lors de la création des stickers: {str(e)}")
            # On continue même si les stickers échouent
        
        # Succès!
        success_message = f"✅ Serveur copié avec succès!\n**Source:** {source_name} (ID: {source_id})\n**Cible:** {target_name} (ID: {target_id})"
        await message.edit(content=success_message)
        
        return {'success': True, 'message': success_message}
        
    except Exception as e:
        error_message = f"❌ Erreur pendant la copie du serveur: {str(e)}"
        logger.error(error_message)
        await message.edit(content=error_message)
        return {'success': False, 'message': error_message}
    
    finally:
        # S'assurer que la session est fermée
        try:
            await discord_api.close()
        except:
            pass

def handle_copy_completion(task, ctx):
    """Gère la fin d'une tâche de copie (réussie ou non)."""
    try:
        # Récupérer le résultat si la tâche est terminée sans erreur
        if not task.exception():
            result = task.result()
            logger.info(f"Tâche de copie terminée pour {ctx.author.name} avec statut: {result.get('success')}")
    except Exception as e:
        logger.error(f"Erreur dans le gestionnaire de fin de tâche: {str(e)}")

if __name__ == "__main__":
    # Récupérer le token du bot depuis les variables d'environnement
    bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    
    if not bot_token:
        logger.error("Aucun token de bot Discord trouvé. Définissez la variable d'environnement DISCORD_BOT_TOKEN.")
        sys.exit(1)
    
    # Lancer le bot
    bot.run(bot_token)