"""Execução das receitas receitas/<id>.sh (funções `instalar` e `executar`)."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from . import caminhos
from .catalogo import Jogo, verificar


def _ambiente(jogo: Jogo) -> dict[str, str]:
    encontrados = [v.caminho for v in verificar(jogo) if v.caminho]
    return {
        **os.environ,
        "JOGO_ID": jogo.id,
        "JOGO_DIR": str(jogo.pasta),
        "ORIGINAIS_DIR": str(caminhos.originais()),
        "ORIGINAL": str(encontrados[0]) if encontrados else "",
    }


def _script(jogo: Jogo, funcao: str, log: Path | None = None) -> str:
    linhas = [
        "set -euo pipefail",
        f"source {shlex.quote(str(caminhos.RECEITAS / '_lib.sh'))}",
        f"source {shlex.quote(str(jogo.arquivo_receita))}",
        'mkdir -p "$JOGO_DIR"',
    ]
    if log:
        linhas.append(f"exec >>{shlex.quote(str(log))} 2>&1")
    linhas.append(funcao)
    return "\n".join(linhas)


def instalar(jogo: Jogo) -> int:
    """Roda `instalar` da receita mostrando a saída no terminal; marca o jogo como instalado."""
    retorno = subprocess.run(["bash", "-c", _script(jogo, "instalar")], env=_ambiente(jogo)).returncode
    if retorno == 0:
        (jogo.pasta / ".instalado").touch()
    return retorno


def comando_jogar(jogo: Jogo, gamescope: bool = False) -> tuple[list[str], dict[str, str]]:
    """Comando que abre o jogo, com a saída indo para ~/AllGames/logs/<id>.log."""
    caminhos.logs().mkdir(parents=True, exist_ok=True)
    log = caminhos.logs() / f"{jogo.id}.log"
    argv = ["bash", "-c", _script(jogo, "executar", log)]
    env = _ambiente(jogo)
    if gamescope and shutil.which("gamescope"):
        # Renderiza o jogo direto na resolução/FPS que o celular pediu ao Sunshine.
        largura = env.get("SUNSHINE_CLIENT_WIDTH", "1920")
        altura = env.get("SUNSHINE_CLIENT_HEIGHT", "1080")
        fps = env.get("SUNSHINE_CLIENT_FPS", "60")
        argv = ["gamescope", "-f", "-W", largura, "-H", altura, "-r", fps, "--", *argv]
    return argv, env


def jogar(jogo: Jogo, gamescope: bool = False) -> None:
    """Substitui o processo atual pelo jogo, para o Sunshine controlar o ciclo de vida."""
    argv, env = comando_jogar(jogo, gamescope)
    os.execvpe(argv[0], argv, env)
