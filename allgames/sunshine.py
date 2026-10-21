"""Publica os jogos instalados como apps do Sunshine (apps.json)."""

import copy
import json
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from . import caminhos
from .catalogo import Jogo

SERVICOS = ("app-dev.lizardbyte.app.Sunshine", "sunshine")

# Reconhece apps criados pelo AllGames mesmo que o repositório mude de lugar.
_NOSSO_CMD = re.compile(r"""(^|/)allgames["']?\s+jogar\s""")

APPS_PADRAO = {
    "env": {"PATH": "$(PATH):$(HOME)/.local/bin"},
    "apps": [{"name": "Desktop", "image-path": "desktop.png"}],
}


def arquivo_apps() -> Path:
    """apps.json em uso, respeitando `file_apps` do sunshine.conf."""
    pasta = caminhos.config_sunshine()
    conf = pasta / "sunshine.conf"
    if conf.exists():
        for linha in conf.read_text(errors="replace").splitlines():
            chave, _, valor = linha.partition("=")
            if chave.strip() == "file_apps" and valor.strip():
                caminho = Path(valor.strip()).expanduser()
                return caminho if caminho.is_absolute() else pasta / caminho
    return pasta / "apps.json"


def _citar(texto: str) -> str:
    return f'"{texto}"' if " " in texto else texto


def app_do_jogo(jogo: Jogo, capa: Path | None, gamescope: bool = False) -> dict:
    opcoes = " --gamescope" if gamescope else ""
    app = {
        "name": jogo.nome,
        "cmd": f"{_citar(str(caminhos.EXECUTAVEL))} jogar{opcoes} {shlex.quote(jogo.id)}",
        "auto-detach": True,
        "wait-all": True,
        "exit-timeout": 5,
    }
    if capa:
        app["image-path"] = str(capa)
    return app


def eh_nosso(app: dict) -> bool:
    return bool(_NOSSO_CMD.search(app.get("cmd", "")))


def mesclar(atual: dict, nossos: list[dict]) -> tuple[dict, list[str]]:
    """Troca os apps do AllGames pelos novos e preserva os que você criou à mão.

    Devolve o novo conteúdo e os nomes que não puderam entrar porque já existe
    um app seu com o mesmo nome.
    """
    seus = [app for app in atual.get("apps", []) if not eh_nosso(app)]
    nomes_seus = {app.get("name") for app in seus}
    conflitos = [app["name"] for app in nossos if app["name"] in nomes_seus]
    novos = [app for app in nossos if app["name"] not in nomes_seus]
    return {**atual, "apps": seus + sorted(novos, key=lambda a: a["name"].lower())}, conflitos


def ler(arquivo: Path) -> dict:
    if not arquivo.exists():
        return copy.deepcopy(APPS_PADRAO)
    return json.loads(arquivo.read_text())


def gravar(arquivo: Path, conteudo: dict) -> Path | None:
    """Grava apps.json guardando uma cópia do anterior. Devolve o caminho do backup."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if arquivo.exists():
        backup = arquivo.with_name(f"{arquivo.name}.{time.strftime('%Y%m%d-%H%M%S')}.bak")
        shutil.copy2(arquivo, backup)
    temporario = arquivo.with_suffix(".tmp")
    temporario.write_text(json.dumps(conteudo, indent=4, ensure_ascii=False) + "\n")
    temporario.replace(arquivo)
    return backup


def servico_ativo() -> str | None:
    if not shutil.which("systemctl"):
        return None
    for nome in SERVICOS:
        r = subprocess.run(["systemctl", "--user", "is-active", nome], capture_output=True, text=True)
        if r.stdout.strip() == "active":
            return nome
    return None


def reiniciar() -> bool:
    """O Sunshine só relê o apps.json ao iniciar, então reinicia o serviço se ele estiver rodando."""
    nome = servico_ativo()
    if not nome:
        return False
    return subprocess.run(["systemctl", "--user", "restart", nome]).returncode == 0
