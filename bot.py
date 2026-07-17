"""
Ponto de entrada do bot.

- Posta um painel com o botão "Abrir Ticket" (comando /painel ou canal fixo).
- Ao clicar, cria uma thread privada e inicia o fluxo de perguntas.
- Comandos administrativos: /painel, /listar, /fechar.
"""
import discord
from discord import app_commands
from discord.ext import commands

import config
from ticket import TicketFlow
import storage

intents = discord.Intents.default()
intents.message_content = True  # necessário para ler textos/anexos no fluxo
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --------------------------------------------------------------------------
# Painel com botão persistente
# --------------------------------------------------------------------------
class PainelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # persistente

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.success,
                       emoji="🎫", custom_id="abrir_ticket")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        canal = interaction.channel

        # cria uma thread privada para o ticket
        nome = f"ticket-{interaction.user.display_name}"[:90]
        try:
            thread = await canal.create_thread(
                name=nome,
                type=discord.ChannelType.private_thread,
                invitable=False,
            )
            await thread.add_user(interaction.user)
        except (discord.HTTPException, AttributeError):
            # fallback: thread pública a partir de uma mensagem
            msg = await canal.send(f"Ticket de {interaction.user.mention}")
            thread = await msg.create_thread(name=nome)

        await interaction.followup.send(
            f"Seu ticket foi criado: {thread.mention}", ephemeral=True)

        flow = TicketFlow(bot, thread, interaction.user)
        bot.loop.create_task(flow.run())


# --------------------------------------------------------------------------
# Permissão de admin
# --------------------------------------------------------------------------
def eh_admin(interaction: discord.Interaction) -> bool:
    perms = getattr(interaction.user, "guild_permissions", None)
    if perms and perms.administrator:
        return True
    ids = {r.id for r in getattr(interaction.user, "roles", [])}
    return bool(ids & set(config.ADMIN_ROLE_IDS))


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------
@bot.tree.command(description="Publica o painel com o botão de abrir ticket.")
async def painel(interaction: discord.Interaction):
    if not eh_admin(interaction):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    embed = discord.Embed(
        title="Abertura de Chamados",
        description="Clique no botão abaixo para abrir um ticket e registrar seu atendimento.",
        color=0x2ecc71,
    )
    await interaction.channel.send(embed=embed, view=PainelView())
    await interaction.response.send_message("Painel publicado.", ephemeral=True)


@bot.tree.command(description="Lista chamados salvos (filtro opcional por categoria/mês).")
@app_commands.describe(categoria="Ex: Abertura de OS - UFMT", mes="Ex: Julho 2026")
async def listar(interaction: discord.Interaction, categoria: str = None, mes: str = None):
    if not eh_admin(interaction):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    arquivos = storage.listar_chamados(categoria, mes)
    if not arquivos:
        await interaction.response.send_message("Nenhum chamado encontrado.", ephemeral=True)
        return
    import os
    linhas = [f"• `{os.path.relpath(a, config.STORAGE_ROOT)}`" for a in arquivos[:25]]
    extra = f"\n… e mais {len(arquivos) - 25}." if len(arquivos) > 25 else ""
    await interaction.response.send_message(
        f"**{len(arquivos)} chamado(s):**\n" + "\n".join(linhas) + extra, ephemeral=True)


@bot.tree.command(description="Fecha (arquiva) o ticket atual.")
async def fechar(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message(
            "Use este comando dentro de um ticket.", ephemeral=True)
        return
    await interaction.response.send_message("Fechando o ticket...", ephemeral=True)
    await interaction.channel.edit(archived=True, locked=True)


# --------------------------------------------------------------------------
# Ciclo de vida
# --------------------------------------------------------------------------
@bot.event
async def setup_hook():
    bot.add_view(PainelView())     # reativa o botão após reinício
    await bot.tree.sync()


@bot.event
async def on_ready():
    print(f"Bot online como {bot.user} (id: {bot.user.id})")
    if config.PANEL_CHANNEL_ID:
        canal = bot.get_channel(config.PANEL_CHANNEL_ID)
        if canal:
            embed = discord.Embed(
                title="Abertura de Chamados",
                description="Clique no botão abaixo para abrir um ticket.",
                color=0x2ecc71,
            )
            await canal.send(embed=embed, view=PainelView())


if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        raise SystemExit("Defina DISCORD_TOKEN no arquivo .env")
    bot.run(config.DISCORD_TOKEN)
