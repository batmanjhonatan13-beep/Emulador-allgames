"""Capas dos jogos para a lista do Moonlight.

Ordem de busca: capas/<id>.png do repositório, depois a capa já baixada em
~/AllGames/capas e, por fim, o acervo libretro-thumbnails no GitHub.
"""

import re
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


def obter(jogo: Jogo, baixar: bool = True) -> Path | None:
    local = caminhos.CAPAS_DO_REPO / f"{jogo.id}.png"
    if local.exists():
        return local
    destino = caminhos.capas() / f"{jogo.id}.png"
    if destino.exists():
        return destino
    if not (baixar and jogo.capa):
        return None
    try:
        with urllib.request.urlopen(url_libretro(jogo.capa), timeout=20) as resposta:
            dados = resposta.read()
    except (urllib.error.URLError, TimeoutError):
        return None
    if not dados.startswith(PNG):
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(dados)
    return destino
