"""Private thin client: API owns identity, inventory, progression and confirmations."""

import os
import discord
import httpx
from discord import app_commands


class TowerBot(discord.Client):
    def __init__(self, api=None):
        super().__init__(
            intents=discord.Intents.none(),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.tree = app_commands.CommandTree(self)
        self.api = api or httpx.AsyncClient(
            base_url=os.environ.get("API_URL", "http://localhost:8000"),
            headers={"X-Bot-Key": os.environ["DISCORD_SERVICE_KEY"]},
            timeout=15,
        )
        self.register_commands()

    async def setup_hook(self):
        await self.tree.sync()

    async def close(self):
        await self.api.aclose()
        await super().close()

    async def request(self, interaction, path, body=None, defer=True):
        if body is not None and path != "/discord/link":
            raise ValueError("Discord cannot control the character")
        if defer:
            await interaction.response.defer(ephemeral=True)
        try:
            r = await (
                self.api.get(path) if body is None else self.api.post(path, json=body)
            )
            if r.is_error:
                # Backend error details contain no sessions/service credentials.
                try:
                    message = r.json().get("detail", "Erro no backend")
                except ValueError:
                    message = "Resposta inválida do backend"
                await interaction.followup.send(str(message)[:1800], ephemeral=True)
                return None
            return r.json()
        except (httpx.HTTPError, ValueError):
            await interaction.followup.send(
                "Backend indisponível. Tente novamente.", ephemeral=True
            )
            return None

    async def show(self, interaction, section):
        data = await self.request(
            interaction, f"/discord/{interaction.user.id}/queries/{section}"
        )
        if data is None:
            return
        await interaction.followup.send(embed=render(section, data), ephemeral=True)

    def register_commands(self):
        @self.tree.command(
            name="vincular", description="Vincule sua conta Web com código de uso único"
        )
        async def vincular(interaction: discord.Interaction, codigo: str):
            data = await self.request(
                interaction,
                "/discord/link",
                {"code": codigo, "discord_id": str(interaction.user.id)},
            )
            if data:
                await interaction.followup.send(
                    "Conta vinculada. Use /status. Remova o vínculo pela Web quando necessário.",
                    ephemeral=True,
                )

        for name, section, description in [
            ("personagem", "character", "Consulte seu personagem persistente"),
            ("status", "character", "Vida, energia, XP e saldo compartilhado"),
            ("atributos", "attributes", "Atributos efetivos e pontos disponíveis"),
            ("inventario", "inventory", "Itens reais da mochila"),
            ("equipamentos", "equipment", "Equipamentos em uso"),
            ("localizacao", "location", "Região e posição atuais"),
            ("mapa", "map", "Andar e localização"),
            ("expedicao", "expedition", "Expedição e grupo ativos"),
            ("recompensas", "rewards", "Direitos pendentes na recepção"),
            ("divida", "debt", "Dívida médica e saldo reservado"),
            ("leiloes", "auctions", "Leilões do backend"),
            ("contratos", "contracts", "Contratos e progresso real"),
            ("carteira", "wallet", "Carteira Lunar e situação da transição"),
            ("minerio", "mineral", "Pepitas do seu personagem"),
            ("recuperacao", "recovery", "Recuperação pessoal de itens"),
        ]:

            def make_callback(section):
                async def callback(interaction: discord.Interaction):
                    await self.show(interaction, section)

                return callback

            self.tree.add_command(
                app_commands.Command(
                    name=name, description=description, callback=make_callback(section)
                )
            )


def render(section, data):
    lines = []
    if section == "character":
        c = data["character"]
        lines = [
            c["name"],
            f"Nível {c['level']} · XP {c['xp']} · HP {c['hp']} · Energia {c['energy']}",
            f"Saldo {data['coins_exact']} · Reserva {data['reserved_gold']}",
        ]
    elif section in ("inventory", "equipment"):
        lines = [
            f"#{i['id']} · {i['name']} ×{i['quantity']}"
            + (" · equipado" if i["equipped"] else "")
            for i in data[section]
        ][:30] or ["Nenhum item."]
    elif section == "attributes":
        lines = [
            f"{k}: {v['effective']} (base {v['base']}, equipamento {v['equipment']})"
            for k, v in data["attributes"].items()
        ] + [f"Pontos livres: {data['points']}"]
    elif section in ("wallet", "mineral"):
        assets = data["assets"]
        codes = (
            ["coin_small", "coin_medium", "coin_large"]
            if section == "wallet"
            else ["nugget_small", "nugget_medium", "nugget_large"]
        )
        labels = (
            ["Moeda pequena", "Moeda média", "Moeda grande"]
            if section == "wallet"
            else ["Pepita 100g", "Pepita 500g", "Pepita 1.000g"]
        )
        lines = [
            f"{label}: {assets.get(code,{}).get('quantity','0')}"
            for code, label in zip(codes, labels)
        ]
        weight = sum(
            int(assets.get(code, {}).get("total_weight_mg", "0")) for code in codes
        )
        lines += [
            f"Peso total: {weight} mg",
            "Conversão Lunar ainda inativa; saldo legado: " + data["legacy_balance"],
        ]
    elif section == "recovery":
        lines = [
            f"#{r['id']} · item {r['item_id']} · {r['price']} moedas · "
            + ("recuperado" if r["recovered"] else "aguardando recuperação")
            for r in data["recovery"][:20]
        ]
    elif section == "map":
        lines = [
            f"Andar {data['floor']} · {data['room']} · ({data['x']}, {data['y']})",
            "Salas descobertas: " + ", ".join(data["discovered_rooms"]),
        ]
    elif section == "location":
        lines = [f"Andar {data['floor']} · {data['room']} · ({data['x']}, {data['y']})"]
    elif section == "debt":
        lines = [
            f"Dívida: {data['debt']} · Saldo: {data['balance']} · Reserva de lances: {data['reserved_gold']}"
        ]
    elif section == "rewards":
        lines = [
            f"{data['guild_rewards']['count']} recompensas · {data['guild_rewards']['total']} moedas pendentes.",
            "Resgate junto à recepcionista da Guilda.",
        ]
    elif section == "expedition":
        e = data["expedition"]
        g = data["encounter"]
        lines = [
            (
                f"Expedição #{e['id']} · {e['status']} · inimigos vivos: {e['alive_enemies']}"
                if e
                else "Sem expedição ativa."
            ),
            (
                f"Grupo #{g['id']} · rodada {g['turn']+1}"
                if g
                else "Sem encontro em grupo."
            ),
        ]
    elif section == "contracts":
        lines = [
            f"#{a['id']} {a['contract']['name']} · {a['progress']}/{a['contract']['required']} · {a['status']} · {a['contract']['reward']} moedas"
            for a in data["accepted"][:15]
        ]
        lines += ["Publicações:"] + [
            f"#{d['id']} {d['name']} · {d['available_slots']} vagas · {d['reward']} moedas · {d['status']}"
            for d in data["definitions"][:15]
        ]
    elif section == "auctions":
        lines = [
            f"#{a['id']} · {a['name']} ×{a['quantity']} · poder {a['attributes']['power']} · mínimo {a['next_bid']} · maior lance {a['highest_bid']} · sua reserva {a['own_reserved']} · {a['status']} · término {a['ends_at']}"
            for a in data["auctions"][:20]
        ] or ["Nenhum leilão."]
    description = "\n".join(lines) or "Nenhum registro."
    return discord.Embed(
        title="Dungeon Game · " + section,
        description=discord.utils.escape_mentions(
            discord.utils.escape_markdown(description)
        )[:4000],
        color=0x86AD84,
    )


if __name__ == "__main__":
    TowerBot().run(os.environ["DISCORD_TOKEN"])
