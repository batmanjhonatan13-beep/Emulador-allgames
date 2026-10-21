"""Execução das receitas receitas/<id>.sh (funções `instalar` e `executar`)."""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from . import caminhos, supervisor
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


def _com_gamescope(argv: list[str], env: dict[str, str], gamescope: bool) -> list[str]:
    if not (gamescope and shutil.which("gamescope")):
        return argv
    # Renderiza o jogo direto na resolução/FPS que o celular pediu ao Sunshine.
    largura = env.get("SUNSHINE_CLIENT_WIDTH", "1920")
    altura = env.get("SUNSHINE_CLIENT_HEIGHT", "1080")
    fps = env.get("SUNSHINE_CLIENT_FPS", "60")
    return ["gamescope", "-f", "-W", largura, "-H", altura, "-r", fps, "--", *argv]


def arquivo_log(jogo: Jogo) -> Path:
    caminhos.logs().mkdir(parents=True, exist_ok=True)
    return caminhos.logs() / f"{jogo.chave}.log"


def comando_jogar(jogo: Jogo, gamescope: bool = False) -> tuple[list[str], dict[str, str]]:
    """Comando que abre o jogo, com a saída indo para ~/AllGames/logs/<id>.log."""
    env = _ambiente(jogo)
    argv = ["bash", "-c", _script(jogo, "executar", arquivo_log(jogo))]
    return _com_gamescope(argv, env, gamescope), env


def jogar(jogo: Jogo, gamescope: bool = False) -> None:
    """Substitui o processo atual pelo jogo, para o Sunshine controlar o ciclo de vida."""
    argv, env = comando_jogar(jogo, gamescope)
    os.execvpe(argv[0], argv, env)


def jogar_comando(jogo: Jogo, argv: list[str], gamescope: bool = False, combo_sair: bool = False) -> int:
    """Como `jogar`, para jogos abertos direto por um comando (ROMs, ports).

    Com `combo_sair`, o AllGames fica rodando junto para fechar o jogo quando
    Select+Start for segurado; sem ele, o processo vira o próprio jogo.
    """
    env = dict(os.environ)
    argv = _com_gamescope(argv, env, gamescope)
    if not shutil.which(argv[0]):
        raise RuntimeError(f"{argv[0]} não está instalado no PC")
    log = os.open(arquivo_log(jogo), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.write(log, f"\n$ {shlex.join(argv)}\n".encode())
    if combo_sair:
        return supervisor.rodar(argv, env=env, log=log)
    if sys.platform == "win32":
        # No Windows o exec cria outro processo e encerra este na hora: o portal acharia
        # que o jogo já fechou. Então abre e espera.
        return subprocess.call(argv, env=env, stdout=log, stderr=log)
    os.dup2(log, 1)
    os.dup2(log, 2)
    os.execvpe(argv[0], argv, env)
