"""Capas dos jogos para a lista do Moonlight.

Ordem de busca: capas/<id>.png do repositório, depois a capa já baixada em
~/AllGames/capas e, por fim, o acervo libretro-thumbnails no GitHub.
"""

import re
import threading
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
    # O acervo usa links simbólicos do git para variantes ("(Rev 1).png" aponta
    # para outro arquivo); o GitHub entrega o link como texto com o nome do alvo.
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as resposta:
                dados = resposta.read()
        except (urllib.error.URLError, TimeoutError):
            return None
        if dados.startswith(PNG):
            return dados
        alvo = dados.decode("utf-8", "replace").strip()
        if len(dados) > 300 or not alvo.endswith(".png") or "/" in alvo:
            return None
        url = url.rsplit("/", 1)[0] + "/" + urllib.parse.quote(alvo)
    return None


def obter(jogo: Jogo, baixar: bool = True) -> Path | None:
    local = caminhos.CAPAS_DO_REPO / f"{jogo.id}.png"
    if local.exists():
        return local
    destino = caminhos.capas() / f"{jogo.id}.png"
    if destino.exists():
        return destino
    if not (baixar and jogo.capa):
        return None
    dados = _baixar(url_libretro(jogo.capa))
    if not dados:
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Grava num temporário e troca de uma vez: o portal pode pedir a mesma capa em paralelo.
    temporario = destino.with_name(f".{destino.name}.{threading.get_ident()}")
    temporario.write_bytes(dados)
    temporario.replace(destino)
    return destino
