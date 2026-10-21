"""Capas dos jogos para a lista do Moonlight.

Ordem de busca: capas/<id>.png do repositório, um PNG com o nome da ROM ao lado
dela, a imagem que o EmulationStation do ArkOS/R36S já tinha baixado, a capa já
baixada em ~/AllGames/capas e, por fim, o acervo libretro-thumbnails. No acervo,
o nome da ROM raramente é idêntico ("007 - GoldenEye" x "GoldenEye 007 (USA)"),
então o AllGames baixa a lista de capas do sistema e escolhe a de nome parecido.
"""

import json
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import caminhos
from .catalogo import Jogo

LIBRETRO = "https://raw.githubusercontent.com/libretro-thumbnails/{repo}/master/Named_Boxarts/{nome}.png"
THUMBNAILS = "https://thumbnails.libretro.com/{sistema}/Named_Boxarts/{nome}.png"
INDICE = "https://thumbnails.libretro.com/{sistema}/Named_Boxarts/"
PNG = b"\x89PNG\r\n\x1a\n"
INDICE_VALE = 30 * 86400
_REGIOES = {"usa": 10, "world": 9, "europe": 7, "brazil": 6, "japan": 3}
_RUINS = ("beta", "proto", "demo", "sample", "kiosk", "hack", "pirate", "unl", "aftermarket")
# Onde mais procurar a capa: cartões do R36S misturam jogos de Game Boy, GBC e GBA nas mesmas pastas.
PARECIDOS = {
    "Nintendo - Game Boy Advance": ["Nintendo - Game Boy Color", "Nintendo - Game Boy"],
    "Nintendo - Game Boy Color": ["Nintendo - Game Boy"],
    "Nintendo - Game Boy": ["Nintendo - Game Boy Color"],
}
_indices: dict[str, tuple[float, dict | None]] = {}
_travas: dict[str, threading.Lock] = {}
_trava_travas = threading.Lock()


def url_libretro(capa: str) -> str:
    """'Nintendo - Nintendo 64/Super Mario 64 (USA)' -> URL do PNG no libretro-thumbnails."""
    sistema, _, nome = capa.partition("/")
    repo = sistema.strip().replace(" ", "_")
    # O libretro troca estes caracteres por "_" no nome dos arquivos.
    nome = re.sub(r'[&*/:`<>?\\|"]', "_", nome.strip())
    return LIBRETRO.format(repo=urllib.parse.quote(repo), nome=urllib.parse.quote(nome))


def url_thumbnails(capa: str) -> str:
    """Mesma capa no servidor de capas do libretro (o que o RetroArch usa)."""
    sistema, _, nome = capa.partition("/")
    nome = re.sub(r'[&*/:`<>?\\|"]', "_", nome.strip())
    return THUMBNAILS.format(sistema=urllib.parse.quote(sistema.strip()), nome=urllib.parse.quote(nome))


# ------------------------------------------------------------------ nomes parecidos


def _base(nome: str) -> str:
    """'Legend of Zelda, The - Link's Awakening (USA) [!]' -> 'the legend of zelda links awakening'."""
    nome = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", nome)
    nome = re.sub(r"^(.*?),\s*(The|A|An)\b(.*)$", r"\2 \1\3", nome.strip(), flags=re.I)
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    # O acervo troca "&" por "_": "and", "&" e "_" são ignorados dos dois lados.
    nome = nome.lower().replace("'", "")
    return " ".join(p for p in re.sub(r"[^a-z0-9]+", " ", nome).split() if p != "and")


def _chaves(nome: str) -> list[str]:
    """Formas de comparar: nome limpo, sem a numeração de coleção ("002 Super Mario World") e em ordem alfabética."""
    base = _base(nome)
    sem_numero = re.sub(r"^\d{1,4} (?=[a-z])", "", base)
    sem_um = re.sub(r" 1$", "", sem_numero)  # "Tiny Toon Adventures 1" -> "Tiny Toon Adventures"
    return [c for c in dict.fromkeys([base, sem_numero, sem_um, " ".join(sorted(base.split()))]) if c]


def _pontos(nome: str) -> tuple[int, int]:
    """Preferência entre capas do mesmo jogo: EUA e mundo primeiro; protótipos e demos por último."""
    marcas = " ".join(re.findall(r"\(([^)]*)\)", nome)).lower()
    pontos = max((v for regiao, v in _REGIOES.items() if regiao in marcas), default=0)
    pontos -= 8 * sum(ruim in marcas for ruim in _RUINS)
    return pontos, -len(nome)


def montar_indice(nomes: list[str]) -> dict[str, str]:
    """chave -> a melhor capa com aquela chave."""
    indice: dict[str, str] = {}
    for nome in sorted(nomes, key=_pontos, reverse=True):
        base = _base(nome)
        for chave in (base, " ".join(sorted(base.split()))):
            indice.setdefault(chave, nome)
    return indice


def procurar(indice: dict[str, str], nomes: list[str]) -> str | None:
    """A capa do acervo com o nome mais parecido com algum dos nomes do jogo."""
    for nome in nomes:
        for chave in _chaves(nome):
            if chave in indice:
                return indice[chave]
    return None


def _nomes_do_acervo(sistema: str) -> list[str] | None:
    """Nomes das capas do sistema no acervo, guardados por 30 dias. None se não deu para baixar."""
    cache = caminhos.capas() / ".indices" / f"{sistema}.json"
    try:
        if time.time() - cache.stat().st_mtime < INDICE_VALE:
            return json.loads(cache.read_text())
    except (OSError, ValueError):
        pass
    try:
        with urllib.request.urlopen(INDICE.format(sistema=urllib.parse.quote(sistema)), timeout=60) as resposta:
            pagina = resposta.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        try:
            return json.loads(cache.read_text())  # sem internet: usa a lista antiga
        except (OSError, ValueError):
            return None
    nomes = [urllib.parse.unquote(n) for n in re.findall(r'href="([^"/?]+)\.png"', pagina)]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(nomes, ensure_ascii=False))
    return nomes


def indice(sistema: str) -> dict | None:
    """Índice de capas do sistema. Se a lista não baixou, tenta de novo só depois de 5 minutos."""
    with _trava_travas:
        trava = _travas.setdefault(sistema, threading.Lock())
    with trava:
        if sistema in _indices:
            quando, lista = _indices[sistema]
            if lista is not None or time.monotonic() - quando < 300:
                return lista
        nomes = _nomes_do_acervo(sistema)
        lista = montar_indice(nomes) if nomes is not None else None
        _indices[sistema] = (time.monotonic(), lista)
        return lista


# ------------------------------------------------------------------ download


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


def _no_acervo(jogo: Jogo) -> list[str] | None:
    """Capas a tentar no acervo: a de nome parecido, pela lista do sistema; None se a lista não baixou."""
    sistema, _, nome = jogo.capa.partition("/")
    nomes = [nome, *([jogo.extra["nome_es"]] if jogo.extra.get("nome_es") else []), jogo.nome]
    lista = indice(sistema)
    if lista is None:
        return None
    for outro in [sistema, *PARECIDOS.get(sistema, [])]:
        achado = procurar(lista if outro == sistema else indice(outro) or {}, nomes)
        if achado:
            return [f"{outro}/{achado}"]
    return []


def obter(jogo: Jogo, baixar: bool = True) -> Path | None:
    local = caminhos.CAPAS_DO_REPO / f"{jogo.chave}.png"
    if local.exists():
        return local
    if jogo.extra.get("rom"):
        # Como no EmulationStation: uma imagem com o mesmo nome da ROM, ao lado dela.
        ao_lado = Path(jogo.extra["rom"]).with_suffix(".png")
        if ao_lado.exists():
            return ao_lado
    # A imagem que o EmulationStation do ArkOS já tinha baixado (gamelist.xml).
    if jogo.extra.get("capa_local") and Path(jogo.extra["capa_local"]).exists():
        return Path(jogo.extra["capa_local"])
    destino = caminhos.capas() / f"{jogo.chave}.png"
    if destino.exists():
        return destino
    if not (baixar and jogo.capa):
        return None
    # Não tenta de novo, por uma semana, capas que não existem no acervo.
    falhou = destino.with_suffix(".sem-capa")
    if falhou.exists() and time.time() - falhou.stat().st_mtime < 7 * 86400:
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    rede_falhou = False
    candidatos = _no_acervo(jogo)
    if candidatos is None:
        candidatos = _candidatos(jogo.capa)
    for capa in candidatos:
        dados = _baixar(url_thumbnails(capa))
        if dados is None:
            dados = _baixar(url_libretro(capa))  # servidor de capas fora do ar: tenta o GitHub
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
