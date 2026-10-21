"""Onde o AllGames guarda cada coisa.

Tudo fica em ~/AllGames (ou em $ALLGAMES_HOME):
    originais/  arquivos dos seus jogos originais (ROMs, ISOs, MPQs...)
    jogos/<id>/ instalação de cada jogo
    capas/      capas baixadas para o Moonlight
    logs/       saída de cada jogo aberto pelo Sunshine
    backups/    cópias dos saves, feitas antes de cada partida
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOGO = REPO / "catalogo" / "jogos.toml"
RECEITAS = REPO / "receitas"
CAPAS_DO_REPO = REPO / "capas"
EXECUTAVEL = REPO / "bin" / "allgames"
PORTAL = REPO / "portal"


def base() -> Path:
    return Path(os.environ.get("ALLGAMES_HOME", Path.home() / "AllGames")).expanduser()


def originais() -> Path:
    return base() / "originais"


def jogos() -> Path:
    return base() / "jogos"


def capas() -> Path:
    return base() / "capas"


def logs() -> Path:
    return base() / "logs"


def backups() -> Path:
    return base() / "backups"


def config_sunshine() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(xdg) / "sunshine"
