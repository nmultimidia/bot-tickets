"""
Motor do ticket. Conduz o colaborador pelo fluxo de perguntas do fluxograma,
coleta textos e fotos, gera o PDF e salva na estrutura de pastas.
"""
import asyncio
from datetime import datetime

import discord

import flow
import storage
from config import STEP_TIMEOUT
from pdf_generator import gerar_pdf, extrair_localizacao

# Palavras que o colaborador digita para encerrar o envio de várias fotos
PALAVRAS_FIM = {"pronto", "fim", "ok", "concluir", "finalizar"}


class SelectView(discord.ui.View):
    """Menu suspenso genérico que resolve um Future com a opção escolhida."""

    def __init__(self, opcoes, autor_id, placeholder="Selecione..."):
        super().__init__(timeout=STEP_TIMEOUT)
        self.autor_id = autor_id
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()
        select = discord.ui.Select(
            placeholder=placeholder,
            options=[discord.SelectOption(label=o) for o in opcoes],
        )
        select.callback = self._on_select
        self._select = select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "Apenas quem abriu o ticket pode responder.", ephemeral=True)
            return
        await interaction.response.defer()
        if not self.future.done():
            self.future.set_result(self._select.values[0])
        self.stop()


class YesNoView(discord.ui.View):
    def __init__(self, autor_id):
        super().__init__(timeout=STEP_TIMEOUT)
        self.autor_id = autor_id
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

    async def _responder(self, interaction, valor):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "Apenas quem abriu o ticket pode responder.", ephemeral=True)
            return
        await interaction.response.defer()
        if not self.future.done():
            self.future.set_result(valor)
        self.stop()

    @discord.ui.button(label="Sim", style=discord.ButtonStyle.success)
    async def sim(self, interaction: discord.Interaction, _):
        await self._responder(interaction, "Sim")

    @discord.ui.button(label="Não", style=discord.ButtonStyle.danger)
    async def nao(self, interaction: discord.Interaction, _):
        await self._responder(interaction, "Não")


class TicketFlow:
    def __init__(self, bot, thread: discord.Thread, autor: discord.Member):
        self.bot = bot
        self.thread = thread
        self.autor = autor
        self.transcricao = []   # [(autor, texto)]
        self.respostas = []     # [{label, type, valor/imagens}]
        self.localizacao = None

    # -- utilidades de conversa ------------------------------------------

    async def _bot_diz(self, texto, view=None):
        self.transcricao.append(("Bot", texto))
        return await self.thread.send(texto, view=view)

    def _check_msg(self, m):
        return m.author.id == self.autor.id and m.channel.id == self.thread.id

    async def _aguardar_msg(self):
        msg = await self.bot.wait_for("message", check=self._check_msg, timeout=STEP_TIMEOUT)
        return msg

    async def _ask_select(self, pergunta, opcoes):
        view = SelectView(opcoes, self.autor.id, placeholder=pergunta[:100])
        await self._bot_diz(pergunta, view=view)
        escolha = await view.future
        self.transcricao.append((self.autor.display_name, escolha))
        return escolha

    async def _ask_yesno(self, pergunta):
        view = YesNoView(self.autor.id)
        await self._bot_diz(pergunta, view=view)
        resp = await view.future
        self.transcricao.append((self.autor.display_name, resp))
        return resp

    async def _ask_text(self, pergunta):
        await self._bot_diz(pergunta)
        msg = await self._aguardar_msg()
        self.transcricao.append((self.autor.display_name, msg.content))
        return msg.content.strip()

    async def _ask_number(self, pergunta):
        while True:
            texto = await self._ask_text(pergunta + " (apenas números)")
            limpo = texto.replace(",", ".").strip()
            try:
                float(limpo)
                return limpo
            except ValueError:
                await self._bot_diz("Valor inválido. Envie apenas números, por favor.")

    async def _coletar_fotos(self, pergunta, multiplas, opcional=False):
        extra = ""
        if multiplas:
            extra = " Você pode enviar várias; digite **pronto** quando terminar."
        if opcional:
            extra += " (ou digite **pular** para não enviar)"
        await self._bot_diz(pergunta + extra)

        imagens = []
        while True:
            msg = await self._aguardar_msg()
            conteudo = msg.content.strip().lower()

            if opcional and conteudo in {"pular", "nao", "não"} and not msg.attachments:
                self.transcricao.append((self.autor.display_name, "(sem foto)"))
                break

            if msg.attachments:
                for att in msg.attachments:
                    if att.content_type and att.content_type.startswith("image"):
                        imagens.append(await att.read())
                self.transcricao.append(
                    (self.autor.display_name, f"[{len(msg.attachments)} anexo(s)]"))
                if not multiplas:
                    break
                await self._bot_diz("Foto recebida. Envie mais ou digite **pronto**.")
                continue

            if multiplas and conteudo in PALAVRAS_FIM:
                if imagens or opcional:
                    break
                await self._bot_diz("Nenhuma foto recebida ainda. Envie ao menos uma.")
                continue

            await self._bot_diz("Por favor, envie uma imagem (anexo).")

        # tenta localização a partir da primeira foto que tiver GPS
        for b in imagens:
            if self.localizacao is None:
                self.localizacao = extrair_localizacao(b)
        return imagens

    # -- execução do fluxo ------------------------------------------------

    async def run(self):
        try:
            await self._bot_diz(
                f"Olá, {self.autor.mention}! Vou abrir seu chamado. "
                f"Responda as perguntas a seguir.")

            categoria = await self._ask_select(
                "Qual o tipo de assunto?", flow.categorias())
            subtipo = await self._ask_select(
                "Qual o tipo de serviço?", flow.subtipos(categoria))

            for etapa in flow.etapas(categoria, subtipo):
                tipo, label = etapa["type"], etapa["label"]

                if tipo == "text":
                    valor = await self._ask_text(label + ":")
                    self.respostas.append({"label": label, "type": "text", "valor": valor})

                elif tipo == "number":
                    valor = await self._ask_number(label + ":")
                    self.respostas.append({"label": label, "type": "number", "valor": valor})

                elif tipo in ("photo", "selfie"):
                    imgs = await self._coletar_fotos(
                        label + ":",
                        multiplas=etapa.get("multiple", False),
                        opcional=etapa.get("optional", False),
                    )
                    self.respostas.append({"label": label, "type": tipo, "imagens": imgs})

                elif tipo == "yesno":
                    valor = await self._ask_yesno(label)
                    self.respostas.append({"label": label, "type": "yesno", "valor": valor})

            await self._finalizar(categoria, subtipo)

        except asyncio.TimeoutError:
            await self.thread.send(
                "⏱️ Tempo esgotado sem resposta. O ticket foi cancelado. "
                "Abra um novo quando quiser.")
        except Exception as e:  # noqa
            await self.thread.send(f"❌ Ocorreu um erro ao processar o ticket: `{e}`")

    async def _finalizar(self, categoria, subtipo):
        await self._bot_diz("Registrando o chamado e gerando o relatório... ⏳")

        quando = datetime.now()
        meta = {
            "colaborador": self.autor.display_name,
            "data_hora": quando,
            "categoria": categoria,
            "subtipo": subtipo,
            "localizacao": self.localizacao,
        }

        caminho = storage.montar_caminho(categoria, subtipo, self.autor.display_name, quando)
        gerar_pdf(caminho, meta=meta, respostas=self.respostas, transcricao=self.transcricao)

        import os
        nome = os.path.basename(caminho)
        await self.thread.send(
            f"✅ **Chamado finalizado!**\n"
            f"Colaborador: **{self.autor.display_name}**\n"
            f"Categoria: **{categoria}** • Tipo: **{subtipo}**\n"
            f"Data/Hora: **{quando.strftime('%d/%m/%Y %H:%M')}**\n"
            f"Localização: **{self.localizacao or 'não disponível'}**\n"
            f"Arquivo: `{nome}`",
            file=discord.File(caminho),
        )
        # Fecha a thread após alguns segundos
        await asyncio.sleep(2)
        try:
            await self.thread.edit(archived=True, locked=True)
        except discord.HTTPException:
            pass
