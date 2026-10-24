"""Thin Discord client: all character data and linking live in FastAPI."""

import os
import discord
import httpx
from discord import app_commands


class TowerBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.api = httpx.AsyncClient(
            base_url=os.environ.get("API_URL", "http://localhost:8000"),
            headers={"X-Bot-Key": os.environ["DISCORD_SERVICE_KEY"]},
            timeout=15,
        )

    async def setup_hook(self):
        await self.tree.sync()

    async def close(self):
        await self.api.aclose()
        await super().close()


bot = TowerBot()


async def request(interaction, path, body=None):
    await interaction.response.defer(ephemeral=True)
    try:
        response = await (
            bot.api.get(path) if body is None else bot.api.post(path, json=body)
        )
        if response.is_error:
            await interaction.followup.send(
                str(response.json().get("detail", "Erro no backend")), ephemeral=True
            )
            return None
        return response.json()
    except httpx.HTTPError:
        await interaction.followup.send(
            "Backend indisponível. Tente novamente.", ephemeral=True
        )
        return None


@bot.tree.command(
    name="vincular", description="Vincule sua conta web com um código de uso único"
)
async def vincular(interaction: discord.Interaction, codigo: str):
    data = await request(
        interaction,
        "/discord/link",
        {"code": codigo, "discord_id": str(interaction.user.id)},
    )
    if data:
        await interaction.followup.send("Conta vinculada. Use /status.", ephemeral=True)


async def show(interaction, section):
    data = await request(interaction, f"/discord/{interaction.user.id}/state")
    if not data:
        return
    c = data["character"]
    embed = discord.Embed(title=c["name"], color=0x86AD84)
    if section == "inventory":
        embed.description = (
            "\n".join(f'{i["name"]} ×{i["quantity"]}' for i in data["inventory"])
            or "Mochila vazia"
        )
    elif section == "map":
        found = data["atlas"]["secrets"]
        embed.description = (
            f"Andar {c['floor']} · {data['room']['name']}\n"
            f"Posição ({c['x']}, {c['y']}) · segredos: {found['found']}/{found['total']}\n"
            f"Salas conhecidas: {', '.join(r['name'] for r in data['atlas']['rooms'])}"
        )
    else:
        embed.description = f'Nível {c["level"]} · XP {c["xp"]}\nVida {c["hp"]} · Energia {c["energy"]}\nMoedas {c["coins"]} · Força {c["strength"]} · Defesa {c["defense"]}'
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="personagem", description="Consulte seu personagem persistente")
async def personagem(interaction: discord.Interaction):
    await show(interaction, "character")


@bot.tree.command(name="status", description="Consulte vida, atributos e saldo")
async def status(interaction: discord.Interaction):
    await show(interaction, "character")


@bot.tree.command(name="inventario", description="Consulte seus itens reais")
async def inventario(interaction: discord.Interaction):
    await show(interaction, "inventory")


@bot.tree.command(name="mapa", description="Consulte andar e posição")
async def mapa(interaction: discord.Interaction):
    await show(interaction, "map")


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
