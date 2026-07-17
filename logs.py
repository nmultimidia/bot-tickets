"""
Roteamento dos logs administrativos para canais específicos.

Preferência: usa o ID do canal salvo via comando /definir_log
(à prova de renomeação — o ID nunca muda).
Se ainda não foi definido para um tipo, cai no NOME do canal como
fallback, então funciona de cara. A config fica em log_config.json.
"""
import json
import os

CONFIG_PATH = os.getenv("LOG_CONFIG_PATH", "log_config.json")

# tipo -> (rótulo amigável, trecho do nome usado no fallback)
LOG_TIPOS = {
    "msg_editada":  ("Mensagens editadas", "logs-msg-editada"),
    "msg_deletada": ("Mensagens deletadas", "logs-msg-deletas"),
    "entrada":      ("Entrada de membros", "logs-entrada"),
    "saida":        ("Saída de membros", "logs-saida"),
    "ticket":       ("Tickets gerados", "logs-tickets-gerados"),
}

_cache = {}


def _load():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def definir(guild_id, tipo, channel_id):
    """Salva o canal (por ID) para um tipo de log."""
    if tipo not in LOG_TIPOS:
        return False
    data = _load()
    data.setdefault(str(guild_id), {})[tipo] = int(channel_id)
    _save(data)
    _cache.pop((guild_id, tipo), None)
    return True


def remover(guild_id, tipo):
    """Remove a definição de um tipo (volta ao fallback por nome)."""
    data = _load()
    g = data.get(str(guild_id), {})
    if tipo in g:
        del g[tipo]
        _save(data)
        _cache.pop((guild_id, tipo), None)
        return True
    return False


def canal_de_log(guild, tipo):
    """Devolve o canal do tipo: 1) por ID salvo, 2) por nome (fallback)."""
    if guild is None or tipo not in LOG_TIPOS:
        return None
    key = (guild.id, tipo)
    if key in _cache:
        return _cache[key]

    canal = None
    cid = _load().get(str(guild.id), {}).get(tipo)
    if cid:
        canal = guild.get_channel(int(cid))
    if canal is None:  # fallback por trecho do nome
        slug = LOG_TIPOS[tipo][1]
        canal = next((ch for ch in guild.text_channels if slug in ch.name), None)

    _cache[key] = canal
    return canal


async def enviar(guild, tipo, embed):
    """Envia o embed para o canal do tipo, se existir. Devolve o canal usado."""
    canal = canal_de_log(guild, tipo)
    if canal is None:
        return None
    try:
        await canal.send(embed=embed)
    except Exception as e:  # sem permissão, canal apagado etc.
        print(f"Falha ao enviar log '{tipo}':", e)
    return canal


def configuracao_atual(guild):
    """Lista (rótulo, canal) de cada tipo, para exibir no /ver_logs."""
    linhas = []
    for tipo, (rotulo, _) in LOG_TIPOS.items():
        c = canal_de_log(guild, tipo)
        linhas.append((rotulo, c.mention if c else "— não definido —"))
    return linhas
