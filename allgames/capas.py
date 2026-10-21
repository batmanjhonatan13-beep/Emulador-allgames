"""Capas dos jogos para a lista do Moonlight.

Ordem de busca: capas/<id>.png do repositório, um PNG com o nome da ROM ao lado
dela, a capa já baixada em ~/AllGames/capas e, por fim, o acervo
libretro-thumbnails no GitHub.
"""

import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import caminhos
from .catalogo import Jogo

LIBRETRO = "https://raw.githubusercontent.com/libretro-thumbnails/{repo}/master/Named_Boxarts/{nome}.png"
PNG = b"\x89PNG\r\n\x1a\n"


def url_libretro(capa: str) -> str:
    """'Nintendo - Nintendo 64/Super Mario 64 (USA)' -> URL do PNG no libretro-thumbnails."""
    sistema, _, nome = capa.partition("/")
    repo = sistema.strip().replace(" ", "_")
    # O libretro troca estes caracteres por "_" no nome dos arquivos.
    nome = re.sub(r'[&*/:`<>?\\|"]', "_", nome.strip())
    return LIBRETRO.format(repo=urllib.parse.quote(repo), nome=urllib.parse.quote(nome))


def _baixar(url: str) -> bytes | None:
    """O PNG; b"" se a capa não existe no acervo; None se a rede falhou."""
    # O acervo usa links simbólicos do git para variantes ("(Rev 1).png" aponta
    # para outro arquivo); o GitHub entrega o link como texto com o nome do alvo.
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as resposta:
                dados = resposta.read()
        except urllib.error.HTTPError as erro:
            return b"" if erro.code == 404 else None
        except (urllib.error.URLError, TimeoutError):
            return None
        if dados.startswith(PNG):
            return dados
        alvo = dados.decode("utf-8", "replace").strip()
        if len(dados) > 300 or not alvo.endswith(".png") or "/" in alvo:
            return b""
        url = url.rsplit("/", 1)[0] + "/" + urllib.parse.quote(alvo)
    return b""


def _candidatos(capa: str) -> list[str]:
    """O nome exato e, para ROMs com marcações como [!] ou [b1], o nome sem elas."""
    sem_colchetes = re.sub(r"\s*\[[^\]]*\]", "", capa).strip()
    return list(dict.fromkeys([capa, sem_colchetes]))


def obter(jogo: Jogo, baixar: bool = True) -> Path | None:
    local = caminhos.CAPAS_DO_REPO / f"{jogo.chave}.png"
    if local.exists():
        return local
    if jogo.extra.get("rom"):
        # Como no EmulationStation: uma imagem com o mesmo nome da ROM, ao lado dela.
        ao_lado = Path(jogo.extra["rom"]).with_suffix(".png")
        if ao_lado.exists():
            return ao_lado
    destino = caminhos.capas() / f"{jogo.chave}.png"
    if destino.exists():
        return destino
    if not (baixar and jogo.capa):
        return None
    # Não tenta de novo, por uma semana, capas que não existem no acervo.
    falhou = destino.with_suffix(".falhou")
    if falhou.exists() and time.time() - falhou.stat().st_mtime < 7 * 86400:
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    rede_falhou = False
    for capa in _candidatos(jogo.capa):
        dados = _baixar(url_libretro(capa))
        if dados:
            # Grava num temporário e troca de uma vez: o portal pode pedir a mesma capa em paralelo.
            temporario = destino.with_name(f".{destino.name}.{threading.get_ident()}")
            temporario.write_bytes(dados)
            temporario.replace(destino)
            return destino
        rede_falhou = rede_falhou or dados is None
    if not rede_falhou:
        falhou.touch()
    return None
