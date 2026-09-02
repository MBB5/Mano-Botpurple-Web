"""
Cog Discord pour La Baguette de Mano.
Gère les commandes liées aux baguettes et kits d'artisanat.
"""

import discord
from discord.ext import commands
from discord import app_commands

from La_Baguette_de_Mano import service_baguettes


class BaguetteCog(commands.Cog, name="La Baguette de Mano"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ===== Commandes spécifiques La Baguette de Mano =====

    baguette_group = app_commands.Group(
        name="baguette",
        description="Commandes dédiées à La Baguette de Mano (prix, recettes, kits)"
    )

    @baguette_group.command(name="prix", description="Affiche le prix d'une baguette")
    @app_commands.describe(
        type="Vente ou Réparation",
        nom="Nom de la baguette"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Vente", value="vente"),
        app_commands.Choice(name="Réparation", value="repa"),
    ])
    async def baguette_prix_cmd(self, interaction: discord.Interaction, type: str, nom: str):
        await self.afficher_prix(interaction, type, nom)

    @baguette_prix_cmd.autocomplete('nom')
    async def baguette_prix_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.autocomplete_nom_prix(interaction, current)

    @baguette_group.command(name="recette", description="Affiche la recette d'une baguette ou d'un kit")
    @app_commands.describe(nom="Nom de la baguette ou du kit")
    async def baguette_recette_cmd(self, interaction: discord.Interaction, nom: str):
        await self.afficher_recette(interaction, nom)

    @baguette_recette_cmd.autocomplete('nom')
    async def baguette_recette_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.autocomplete_nom_recette(interaction, current)

    @baguette_group.command(name="catalogue", description="Affiche le catalogue complet des prix de baguettes")
    @app_commands.describe(type="Vente ou Réparation")
    @app_commands.choices(type=[
        app_commands.Choice(name="Vente", value="vente"),
        app_commands.Choice(name="Réparation", value="repa"),
    ])
    async def baguette_catalogue_cmd(self, interaction: discord.Interaction, type: str):
        await self.afficher_catalogue(interaction, type)

    # ===== Méthodes de rendu réutilisables =====

    async def afficher_prix(self, interaction: discord.Interaction, type_action: str, nom: str):
        data = service_baguettes.charger_prix()
        cle = service_baguettes.get_prix_cle(type_action)
        liste_objets = data.get(cle, {})
        type_label = "Vente" if type_action == "vente" else "Réparation"

        cle_trouvee = service_baguettes.trouver_cle(liste_objets, nom)
        if not cle_trouvee:
            dispos = list(liste_objets.keys())
            msg = f"❌ **{nom}** est introuvable dans La Baguette de Mano ({type_label})."
            if dispos:
                apercu = ", ".join(f"`{d}`" for d in dispos[:15])
                if len(dispos) > 15:
                    apercu += f" ... et {len(dispos) - 15} autre(s)"
                msg += f"\n\n📋 **Baguettes disponibles :**\n{apercu}"
            else:
                msg += "\n\nℹ️ Aucune baguette enregistrée pour le moment."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        info = liste_objets[cle_trouvee]
        embed = discord.Embed(
            title=f"🪄 La Baguette de Mano — {cle_trouvee}",
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
        data = service_baguettes.charger_recettes()
        b_dict = data.get('Recettesbaguettes', {})
        cle_trouvee = service_baguettes.trouver_cle(b_dict, nom)

        if not cle_trouvee:
            dispos = list(b_dict.keys())
            msg = f"❌ Aucune recette de baguette/kit trouvée pour **{nom}**."
            if dispos:
                msg += "\n\n📋 **Recettes disponibles :**\n" + ", ".join(f"`{d}`" for d in dispos[:15])
            await interaction.response.send_message(msg, ephemeral=True)
            return

        item = b_dict[cle_trouvee]
        is_kit = "kit" in cle_trouvee.lower() or "guide" in cle_trouvee.lower()
        embed = discord.Embed(
            title=f"{'📦' if is_kit else '🪄'} Recette : {cle_trouvee}",
            color=discord.Color.gold() if is_kit else discord.Color.teal()
        )
        embed.description = f"**Programme :** {'Artisanat & Kits' if is_kit else 'La Baguette de Mano'}"

        if isinstance(item, dict):
            ingr_texte = item.get("ingredients") or item.get("recette") or ""
            analyse = service_baguettes.analyser_composants_recette(ingr_texte)

            if item.get("ingredients"):
                embed.add_field(name="🧪 Ingrédients / Composants", value=str(item["ingredients"]), inline=False)
            if item.get("details"):
                embed.add_field(name="🔨 Fabrication / Instructions", value=str(item["details"]), inline=False)
            if item.get("recette"):
                embed.add_field(name="📜 Détails", value=str(item["recette"]), inline=False)

            # Synthèse Cristaux Solaires, Magicarium, Coûts & Temps de récolte
            if analyse["kits_base"] > 0 or analyse["cristaux_extra"] > 0 or analyse["magicarium"] > 0:
                lignes_synthese = []
                if analyse["kits_base"] > 0:
                    lignes_synthese.append(f"📦 **Kits de base requis :** {int(analyse['kits_base']):,} kits".replace(',', ' '))
                if analyse["cristaux_extra"] > 0:
                    lignes_synthese.append(f"☀️ **Cristaux Solaires (hors kit de base) :** {int(analyse['cristaux_extra']):,}".replace(',', ' '))
                if analyse["magicarium"] > 0:
                    prix_u_mag = int(service_baguettes.TARIF_MAGICARIUM_DEFAUT)
                    lignes_synthese.append(
                        f"🔮 **Magicarium requis :** {int(analyse['magicarium']):,} "
                        f"*({prix_u_mag:,} G/u = {int(analyse['cout_magicarium']):,} Galyons)*".replace(',', ' ')
                    )
                if analyse["cout_kits"] > 0:
                    lignes_synthese.append(f"💰 **Coût estimé des kits :** {int(analyse['cout_kits']):,} Galyons *(3 200 G/kit)*".replace(',', ' '))
                if analyse["cout_total"] > 0:
                    lignes_synthese.append(f"🪙 **Coût total estimé (Kits + Magicarium) :** **{int(analyse['cout_total']):,} Galyons**".replace(',', ' '))
                if analyse["temps_recolte_minutes"] > 0:
                    mins_totales = int(analyse["temps_recolte_minutes"])
                    heures = mins_totales // 60
                    mins_restantes = mins_totales % 60
                    if heures > 0:
                        temps_formatte = f"{mins_totales:,} min (~{heures}h{f'{mins_restantes:02d}' if mins_restantes > 0 else ''})".replace(',', ' ')
                    else:
                        temps_formatte = f"{mins_totales} min"
                    lignes_synthese.append(f"⏱️ **Temps estimé de récolte (19 min/kit) :** {temps_formatte}")

                # Recherche du Prix de Vente PNJ
                prix_data = service_baguettes.charger_prix()
                ventes = prix_data.get("Prixdeventesbaguettes", {})
                cle_prix = service_baguettes.trouver_cle(ventes, cle_trouvee)
                if cle_prix and isinstance(ventes[cle_prix], dict):
                    pnj_texte = ventes[cle_prix].get("pnj")
                    if pnj_texte and pnj_texte != "?":
                        lignes_synthese.append(f"🪙 **Prix de vente PNJ :** **{pnj_texte}**")

                embed.add_field(name="📊 Synthèse des Composants Clés", value="\n".join(lignes_synthese), inline=False)
            else:
                # Si aucun kit/magicarium mais prix PNJ existant
                prix_data = service_baguettes.charger_prix()
                ventes = prix_data.get("Prixdeventesbaguettes", {})
                cle_prix = service_baguettes.trouver_cle(ventes, cle_trouvee)
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
        data = service_baguettes.charger_prix()
        cle = service_baguettes.get_prix_cle(type_action)
        liste_objets = data.get(cle, {})
        type_label = "Vente" if type_action == "vente" else "Réparation"

        if not liste_objets:
            await interaction.response.send_message(
                f"ℹ️ Aucune baguette enregistrée ({type_label}).", ephemeral=True
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
            titre=f"🪄 Catalogue La Baguette de Mano — {type_label}",
            description=f"Total : **{len(liste_objets)}** baguette(s)",
            lignes_items=lignes,
            color=discord.Color.gold()
        )

    # ===== Autocomplétion =====

    async def autocomplete_nom_prix(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        t = getattr(interaction.namespace, 'type', 'vente') or 'vente'
        data = service_baguettes.charger_prix()
        cle = service_baguettes.get_prix_cle(t)
        liste = list(data.get(cle, {}).keys())
        current_norm = service_baguettes.singulariser(current)
        matches = [k for k in liste if not current_norm or current_norm in service_baguettes.singulariser(k)]
        return [app_commands.Choice(name=k[:100], value=k[:100]) for k in matches[:25]]

    async def autocomplete_nom_recette(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        all_ordered = service_baguettes.lister_recettes_ordonnees()
        current_norm = service_baguettes.singulariser(current or "")
        matches = []
        for k, tag in all_ordered:
            if not current_norm or current_norm in service_baguettes.singulariser(k):
                label = f"{k} ({tag})" if len(f"{k} ({tag})") <= 100 else k[:100]
                matches.append(app_commands.Choice(name=label, value=k))
                if len(matches) >= 25:
                    break
        return matches


async def setup(bot: commands.Bot):
    await bot.add_cog(BaguetteCog(bot))
