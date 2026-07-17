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
import logs as logmod
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

        embed = discord.Embed(
            title="🎫 Novo ticket criado",
            description=(f"Colaborador: {interaction.user.mention}\n"
                         f"Thread: {thread.mention}"),
            color=0x3498db,
        )
        embed.timestamp = discord.utils.utcnow()
        await logmod.enviar(interaction.guild, "ticket", embed)

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
# Configuração dos canais de log (/definir_log, /ver_logs)
# --------------------------------------------------------------------------
_TIPO_CHOICES = [
    app_commands.Choice(name=rotulo, value=tipo)
    for tipo, (rotulo, _slug) in logmod.LOG_TIPOS.items()
]


@bot.tree.command(description="Define ESTE canal como destino de um tipo de log.")
@app_commands.describe(tipo="Qual tipo de log deve cair neste canal")
@app_commands.choices(tipo=_TIPO_CHOICES)
async def definir_log(interaction: discord.Interaction, tipo: app_commands.Choice[str]):
    if not eh_admin(interaction):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    logmod.definir(interaction.guild_id, tipo.value, interaction.channel_id)
    await interaction.response.send_message(
        f"✅ Logs de **{tipo.name}** agora vão para {interaction.channel.mention}.",
        ephemeral=True)


@bot.tree.command(description="Mostra qual canal recebe cada tipo de log.")
async def ver_logs(interaction: discord.Interaction):
    if not eh_admin(interaction):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    linhas = logmod.configuracao_atual(interaction.guild)
    await interaction.response.send_message(
        "\n".join(f"• **{r}**: {c}" for r, c in linhas), ephemeral=True)


# --------------------------------------------------------------------------
# Logs de mensagens e membros (opcional — MSG_LOGS_ENABLED=true)
# --------------------------------------------------------------------------
def _resumo(texto: str, limite: int = 1000) -> str:
    texto = texto or "*(sem texto — possivelmente apenas anexo/embed)*"
    return texto if len(texto) <= limite else texto[:limite] + "…"


def _eh_canal_de_log(channel) -> bool:
    """Evita registrar eventos ocorridos nos próprios canais de log."""
    return any(logmod.canal_de_log(channel.guild, t) == channel
               for t in logmod.LOG_TIPOS)


@bot.event
async def on_message_delete(message: discord.Message):
    if not config.MSG_LOGS_ENABLED or message.author.bot or message.guild is None:
        return
    if _eh_canal_de_log(message.channel):
        return
    embed = discord.Embed(
        title="🗑️ Mensagem apagada",
        description=(f"Autor: {message.author.mention}\n"
                     f"Canal: {message.channel.mention}\n\n"
                     f"**Conteúdo:**\n{_resumo(message.content)}"),
        color=0xe74c3c,
    )
    if message.attachments:
        embed.add_field(
            name="Anexos",
            value="\n".join(a.filename for a in message.attachments[:10]))
    embed.timestamp = discord.utils.utcnow()
    await logmod.enviar(message.guild, "msg_deletada", embed)


@bot.event
async def on_message_edit(antes: discord.Message, depois: discord.Message):
    if not config.MSG_LOGS_ENABLED or antes.author.bot or antes.guild is None:
        return
    if antes.content == depois.content:
        return  # edições de embed/pin, sem mudança de texto
    if _eh_canal_de_log(antes.channel):
        return
    embed = discord.Embed(
        title="✏️ Mensagem editada",
        description=(f"Autor: {antes.author.mention}\n"
                     f"Canal: {antes.channel.mention} — "
                     f"[ir para a mensagem]({depois.jump_url})\n\n"
                     f"**Antes:**\n{_resumo(antes.content, 500)}\n\n"
                     f"**Depois:**\n{_resumo(depois.content, 500)}"),
        color=0xf39c12,
    )
    embed.timestamp = discord.utils.utcnow()
    await logmod.enviar(antes.guild, "msg_editada", embed)


@bot.event
async def on_member_join(member: discord.Member):
    if not config.MSG_LOGS_ENABLED:
        return
    embed = discord.Embed(
        title="📥 Membro entrou",
        description=(f"{member.mention} (`{member}`)\n"
                     f"Conta criada em: "
                     f"{member.created_at.strftime('%d/%m/%Y %H:%M')}"),
        color=0x2ecc71,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()
    await logmod.enviar(member.guild, "entrada", embed)


@bot.event
async def on_member_remove(member: discord.Member):
    if not config.MSG_LOGS_ENABLED:
        return
    embed = discord.Embed(
        title="📤 Membro saiu",
        description=f"{member.mention} (`{member}`)",
        color=0x95a5a6,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()
    await logmod.enviar(member.guild, "saida", embed)


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
