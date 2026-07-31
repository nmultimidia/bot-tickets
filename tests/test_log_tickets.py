# -*- coding: utf-8 -*-
"""Valida o roteamento do canal de log de tickets."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
import logs  # noqa: E402


class GuildFalso:
    def __init__(self, guild_id, canais):
        self.id = guild_id
        self.text_channels = canais

    def get_channel(self, channel_id):
        return next((c for c in self.text_channels if c.id == channel_id), None)


class CanalFalso:
    def __init__(self, channel_id, nome):
        self.id = channel_id
        self.name = nome


def test_canal_de_log_usa_fallback_por_nome(monkeypatch):
    canais = [
        CanalFalso(1, "geral"),
        CanalFalso(2, "logs-tickets-gerados"),
    ]
    guild = GuildFalso(100, canais)
    monkeypatch.setattr(logs, "_load", lambda: {})
    logs._cache.clear()

    assert logs.canal_de_log(guild, "ticket") is canais[1]


def test_canal_de_log_prefere_id_configurado(monkeypatch):
    canais = [
        CanalFalso(1, "geral"),
        CanalFalso(2, "logs-tickets-gerados"),
    ]
    guild = GuildFalso(100, canais)
    monkeypatch.setattr(logs, "_load", lambda: {"100": {"ticket": 1}})
    logs._cache.clear()

    assert logs.canal_de_log(guild, "ticket") is canais[0]


def test_canal_de_log_usa_config_env_do_ticket(monkeypatch):
    canais = [
        CanalFalso(1, "geral"),
        CanalFalso(2, "logs-tickets"),
    ]
    guild = GuildFalso(100, canais)
    monkeypatch.setattr(logs, "_load", lambda: {})
    logs._cache.clear()
    monkeypatch.setattr(config, "TICKET_LOG_CHANNEL_ID", 0, raising=False)
    monkeypatch.setattr(config, "TICKET_LOG_CANAL_NOME", "logs-tickets", raising=False)

    assert logs.canal_de_log(guild, "ticket") is canais[1]


def test_canal_de_log_falha_graciosamente(monkeypatch):
    guild = GuildFalso(100, [CanalFalso(1, "geral")])
    monkeypatch.setattr(logs, "_load", lambda: {})
    logs._cache.clear()
    monkeypatch.setattr(config, "TICKET_LOG_CHANNEL_ID", 0, raising=False)
    monkeypatch.setattr(config, "TICKET_LOG_CANAL_NOME", "canal-que-nao-existe", raising=False)

    assert logs.canal_de_log(guild, "ticket") is None
