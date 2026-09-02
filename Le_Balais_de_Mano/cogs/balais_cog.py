"""
Cog Discord pour Le Balais de Mano.
Gère les commandes liées aux balais (prix, recettes, catalogue).
"""

import discord
from discord.ext import commands
from discord import app_commands

from Le_Balais_de_Mano import service_balais


class BalaisCog(commands.Cog, name="Le Balais de Mano"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ===== Commandes spécifiques Le Balais de Mano =====

    balais_group = app_commands.Group(
        name="balais",
        description="Commandes dédiées au Balais de Mano (prix, recettes, catalogue)"
    )

    @balais_group.command(name="prix", description="Affiche le prix d'un balai")
    @app_commands.describe(
        type="Vente ou Réparation",
        nom="Nom du balai"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Vente", value="vente"),
        app_commands.Choice(name="Réparation", value="repa"),
    ])
    async def balais_prix_cmd(self, interaction: discord.Interaction, type: str, nom: str):
        await self.afficher_prix(interaction, type, nom)

    @balais_prix_cmd.autocomplete('nom')
    async def balais_prix_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.autocomplete_nom_prix(interaction, current)

    @balais_group.command(name="recette", description="Affiche la recette d'un balai")
    @app_commands.describe(nom="Nom du balai")
    async def balais_recette_cmd(self, interaction: discord.Interaction, nom: str):
        await self.afficher_recette(interaction, nom)

    @balais_recette_cmd.autocomplete('nom')
    async def balais_recette_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.autocomplete_nom_recette(interaction, current)

    @balais_group.command(name="catalogue", description="Affiche le catalogue complet des prix de balais")
    @app_commands.describe(type="Vente ou Réparation")
    @app_commands.choices(type=[
        app_commands.Choice(name="Vente", value="vente"),
        app_commands.Choice(name="Réparation", value="repa"),
    ])
    async def balais_catalogue_cmd(self, interaction: discord.Interaction, type: str):
        await self.afficher_catalogue(interaction, type)

    # ===== Méthodes de rendu réutilisables =====

    async def afficher_prix(self, interaction: discord.Interaction, type_action: str, nom: str):
        data = service_balais.charger_prix()
        cle = service_balais.get_prix_cle(type_action)
        liste_objets = data.get(cle, {})
        type_label = "Vente" if type_action == "vente" else "Réparation"

        cle_trouvee = service_balais.trouver_cle(liste_objets, nom)
        if not cle_trouvee:
            dispos = list(liste_objets.keys())
            msg = f"❌ **{nom}** est introuvable dans Le Balais de Mano ({type_label})."
            if dispos:
                apercu = ", ".join(f"`{d}`" for d in dispos[:15])
                if len(dispos) > 15:
                    apercu += f" ... et {len(dispos) - 15} autre(s)"
                msg += f"\n\n📋 **Balais disponibles :**\n{apercu}"
            else:
                msg += "\n\nℹ️ Aucun balai enregistré pour le moment."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        info = liste_objets[cle_trouvee]
        embed = discord.Embed(
            title=f"🧹 Le Balais de Mano — {cle_trouvee}",
            color=discord.Color.gold() if type_action == "vente" else discord.Color.blue()
        )
        embed.description = f"**Type :** {type_label} | **Liste :** `{cle}`"

        if isinstance(info, dict):
            if "stats" in info and info["stats"]:
                embed.add_field(name="📊 Statistiques & Infos", value=str(info["stats"]), inline=False)
            if any(k in info for k in ("coutant", "client", "pnj")):
                embed.add_field(name="💰 Prix Coûtant", value=str(info.get("coutant", "?")), inline=True)
                embed.add_field(name="🏷️ Prix Client", value=str(info.get("client", "?")), inline=True)
                embed.add_field(name="🪙 Prix PNJ", value=str(info.get("pnj", "?")), inline=True)
            if "date" in info:
                embed.set_footer(text=f"Dernière mise à jour : {info['date']}")
        else:
            embed.add_field(name="📊 Statistiques & Infos", value=str(info), inline=False)

        await interaction.response.send_message(embed=embed)

    async def afficher_recette(self, interaction: discord.Interaction, nom: str):
        data = service_balais.charger_recettes()
        b_dict = data.get('Recettesbalais', {})
        cle_trouvee = service_balais.trouver_cle(b_dict, nom)

        if not cle_trouvee:
            dispos = list(b_dict.keys())
            msg = f"❌ Aucune recette de balai trouvée pour **{nom}**."
            if dispos:
                msg += "\n\n📋 **Recettes disponibles :**\n" + ", ".join(f"`{d}`" for d in dispos[:15])
            await interaction.response.send_message(msg, ephemeral=True)
            return

        item = b_dict[cle_trouvee]
        embed = discord.Embed(
            title=f"🧹 Recette : {cle_trouvee}",
            color=discord.Color.purple()
        )
        embed.description = "**Programme :** Le Balais de Mano"

        if isinstance(item, dict):
            if item.get("ingredients"):
                embed.add_field(name="🧪 Ingrédients / Composants", value=str(item["ingredients"]), inline=False)
            if item.get("details"):
                embed.add_field(name="🔨 Fabrication / Instructions", value=str(item["details"]), inline=False)
            if item.get("recette"):
                embed.add_field(name="📜 Détails", value=str(item["recette"]), inline=False)

            # Recherche du Prix de Vente PNJ
            prix_data = service_balais.charger_prix()
            ventes = prix_data.get("Prixdeventesbalais", {})
            cle_prix = service_balais.trouver_cle(ventes, cle_trouvee)
            if cle_prix and isinstance(ventes[cle_prix], dict):
                pnj_texte = ventes[cle_prix].get("pnj")
                if pnj_texte and pnj_texte != "?":
                    embed.add_field(name="🪙 Prix de vente PNJ", value=f"**{pnj_texte}**", inline=False)

            if "date" in item:
                embed.set_footer(text=f"Dernière mise à jour : {item['date']}")
        else:
            embed.add_field(name="📜 Recette", value=str(item), inline=False)

        await interaction.response.send_message(embed=embed)

    async def afficher_catalogue(self, interaction: discord.Interaction, type_action: str):
        data = service_balais.charger_prix()
        cle = service_balais.get_prix_cle(type_action)
        liste_objets = data.get(cle, {})
        type_label = "Vente" if type_action == "vente" else "Réparation"

        if not liste_objets:
            await interaction.response.send_message(
                f"ℹ️ Aucun balai enregistré ({type_label}).", ephemeral=True
            )
            return

        lignes = []
        for nom_item, info in liste_objets.items():
            stat = ""
            if isinstance(info, dict):
                if any(k in info for k in ("client", "coutant", "pnj")):
                    stat = f"Client: {info.get('client', '?')} | Coût: {info.get('coutant', '?')} | PNJ: {info.get('pnj', '?')}"
                elif "stats" in info:
                    stat = info["stats"]
            else:
                stat = str(info)
            lignes.append(f"• **{nom_item}** : {stat}")

        from ManoBotPurple.cogs.pagination_helper import envoyer_liste_decoupee
        await envoyer_liste_decoupee(
            interaction=interaction,
            titre=f"🧹 Catalogue Le Balais de Mano — {type_label}",
            description=f"Total : **{len(liste_objets)}** balai(s)",
            lignes_items=lignes,
            color=discord.Color.purple()
        )

    # ===== Autocomplétion =====

    async def autocomplete_nom_prix(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        t = getattr(interaction.namespace, 'type', 'vente') or 'vente'
        data = service_balais.charger_prix()
        cle = service_balais.get_prix_cle(t)
        liste = list(data.get(cle, {}).keys())
        current_norm = service_balais.singulariser(current)
        matches = [k for k in liste if not current_norm or current_norm in service_balais.singulariser(k)]
        return [app_commands.Choice(name=k[:100], value=k[:100]) for k in matches[:25]]

    async def autocomplete_nom_recette(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        all_ordered = service_balais.lister_recettes_ordonnees()
        current_norm = service_balais.singulariser(current or "")
        matches = []
        for k, tag in all_ordered:
            if not current_norm or current_norm in service_balais.singulariser(k):
                label = f"{k} ({tag})" if len(f"{k} ({tag})") <= 100 else k[:100]
                matches.append(app_commands.Choice(name=label, value=k))
                if len(matches) >= 25:
                    break
        return matches


async def setup(bot: commands.Bot):
    await bot.add_cog(BalaisCog(bot))
