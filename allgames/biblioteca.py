"""A biblioteca completa: catálogo, ROMs das pastas de sistemas e lojas."""

from . import catalogo, lojas, portmaster, sistemas
from .catalogo import Jogo


def todos(jogos_do_catalogo: list[Jogo] | None = None) -> list[Jogo]:
    base = jogos_do_catalogo if jogos_do_catalogo is not None else catalogo.carregar()
    return [*base, *sistemas.jogos(), *lojas.jogos(), *portmaster.jogos()]


def buscar(id_: str, jogos_do_catalogo: list[Jogo] | None = None) -> Jogo:
    if id_.startswith("rom:"):
        jogos = sistemas.jogos()
    elif id_.startswith(("steam:", "heroic:")):
        jogos = lojas.jogos()
    elif id_.startswith("port:"):
        jogos = portmaster.jogos()
    else:
        return catalogo.buscar(jogos_do_catalogo if jogos_do_catalogo is not None else catalogo.carregar(), id_)
    for jogo in jogos:
        if jogo.id == id_:
            return jogo
    raise catalogo.ErroCatalogo(f"jogo {id_!r} não encontrado")
