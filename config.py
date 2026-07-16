"""
Configurações centrais do bot.
Lê variáveis do arquivo .env (veja .env.example).
"""
import os
import re
import unicodedata
from dotenv import load_dotenv

load_dotenv()

# Token do bot (obrigatório) — pegue no Developer Portal do Discord.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# Pasta raiz onde os chamados serão salvos.
# Pode ser uma pasta local, um ponto de montagem de rede (servidor físico)
# ou uma pasta sincronizada com nuvem (Google Drive Desktop, rclone, etc).
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "./chamados")

# ID do canal onde o painel "Abrir Ticket" será postado (opcional).
# Se vazio, use o comando /painel dentro do canal desejado.
PANEL_CHANNEL_ID = int(os.getenv("PANEL_CHANNEL_ID", "0") or "0")

# IDs de cargos com permissão administrativa no bot, separados por vírgula.
ADMIN_ROLE_IDS = [
    int(x) for x in os.getenv("ADMIN_ROLE_IDS", "").replace(" ", "").split(",") if x
]

# Tempo máximo (segundos) que o bot aguarda cada resposta antes de expirar o ticket.
STEP_TIMEOUT = int(os.getenv("STEP_TIMEOUT", "1800"))  # 30 min

# Meses em português para o nome da pasta (ex: "Julho 2026").
MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def camel(texto: str) -> str:
    """Remove acentos e espaços, devolvendo em CamelCase para nome de arquivo.
    Ex: 'OS Instalação' -> 'OSInstalacao'; 'João Silva' -> 'JoaoSilva'."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    partes = re.split(r"[^A-Za-z0-9]+", texto)
    return "".join(p[:1].upper() + p[1:] for p in partes if p)
