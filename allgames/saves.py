"""Saves: onde cada jogo grava o progresso no PC, e as cópias de segurança.

Os jogos rodam no PC, então o progresso fica sempre no PC (o celular só recebe
o vídeo). O campo `saves` do catálogo diz onde cada jogo grava: caminhos
relativos à pasta do jogo (~/AllGames/jogos/<id>), começando com "~/" ou absolutos.
Antes de cada partida o AllGames copia esses arquivos para
~/AllGames/backups/<id>/<data>, guardando as últimas cópias.
"""

import bisect
import fnmatch
import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from . import caminhos
from .catalogo import Jogo

BACKUPS_POR_JOGO = 10
_ASSINATURA = ".assinatura"
_CORINGA = re.compile(r"[*?[]")


class Pastas:
    """Conteúdo de cada pasta, lido uma vez só.

    Com milhares de ROMs numa pasta, procurar "Jogo.state*" com glob relê a pasta
    inteira a cada ROM. O portal usa uma Pastas por atualização da lista.
    """

    def __init__(self):
        self._nomes: dict[str, list[str]] = {}

    def nomes(self, pasta: str) -> list[str]:
        if pasta not in self._nomes:
            try:
                self._nomes[pasta] = sorted(os.listdir(pasta))
            except OSError:
                self._nomes[pasta] = []
        return self._nomes[pasta]

    def buscar(self, pasta: str, padrao: str) -> list[Path]:
        """Como glob(pasta/padrao) para um padrão sem "/": só olha os nomes com o mesmo começo."""
        nomes = self.nomes(pasta)
        prefixo = _CORINGA.split(padrao, 1)[0]
        achados = []
        for i in range(bisect.bisect_left(nomes, prefixo), len(nomes)):
            nome = nomes[i]
            if not nome.startswith(prefixo):
                break
            if fnmatch.fnmatchcase(nome, padrao) and (padrao.startswith(".") or not nome.startswith(".")):
                achados.append(Path(pasta, nome))
        return achados


def _base_e_padrao(jogo: Jogo, padrao: str) -> tuple[Path, str]:
    if padrao.startswith("~/"):
        return Path.home(), padrao[2:]
    if padrao.startswith("/"):
        return Path("/"), padrao[1:]
    return jogo.pasta, padrao


def arquivos(jogo: Jogo, pastas: Pastas | None = None) -> list[Path]:
    pastas = pastas or Pastas()
    encontrados = set()
    for padrao in jogo.saves:
        base, relativo = _base_e_padrao(jogo, padrao)
        pasta, _, nome = str(base / relativo).rpartition("/")
        if not _CORINGA.search(pasta) and "**" not in nome:
            encontrados.update(p for p in pastas.buscar(pasta or "/", nome) if p.is_file())
        elif base.is_dir():
            encontrados.update(p for p in base.glob(relativo) if p.is_file())
    return sorted(encontrados)


def ultimo_save(jogo: Jogo, pastas: Pastas | None = None) -> float | None:
    return max((p.stat().st_mtime for p in arquivos(jogo, pastas)), default=None)


def _no_backup(jogo: Jogo, arquivo: Path) -> Path:
    """Caminho do arquivo dentro de uma cópia: jogo/..., home/... ou raiz/..."""
    if arquivo.is_relative_to(jogo.pasta):
        return Path("jogo") / arquivo.relative_to(jogo.pasta)
    if arquivo.is_relative_to(Path.home()):
        return Path("home") / arquivo.relative_to(Path.home())
    return Path("raiz") / arquivo.relative_to("/")


def _do_backup(jogo: Jogo, relativo: Path) -> Path:
    raiz, *resto = relativo.parts
    base = {"jogo": jogo.pasta, "home": Path.home()}.get(raiz, Path("/"))
    return base.joinpath(*resto)


def _assinatura(jogo: Jogo, lista: list[Path]) -> str:
    h = hashlib.sha1()
    for arquivo in lista:
        h.update(str(_no_backup(jogo, arquivo)).encode())
        h.update(arquivo.read_bytes())
    return h.hexdigest()


def _pasta_backups(jogo: Jogo) -> Path:
    # "rom:snes/Jogo.sfc" -> backups/rom/snes/Jogo.sfc
    return caminhos.backups() / jogo.id.replace(":", "/")


def backups(jogo: Jogo) -> list[Path]:
    pasta = _pasta_backups(jogo)
    return sorted(p for p in pasta.iterdir() if p.is_dir()) if pasta.is_dir() else []


def fazer_backup(jogo: Jogo) -> Path | None:
    """Copia os saves atuais. Não faz nada se não houver saves ou se nada mudou desde a última cópia."""
    lista = arquivos(jogo)
    if not lista:
        return None
    assinatura = _assinatura(jogo, lista)
    anteriores = backups(jogo)
    if anteriores and (anteriores[-1] / _ASSINATURA).exists():
        if (anteriores[-1] / _ASSINATURA).read_text() == assinatura:
            return None

    # Com microssegundos, a ordem alfabética dos nomes é a ordem em que foram feitas.
    destino = _pasta_backups(jogo) / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for arquivo in lista:
        alvo = destino / _no_backup(jogo, arquivo)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arquivo, alvo)
    (destino / _ASSINATURA).write_text(assinatura)

    for antigo in backups(jogo)[:-BACKUPS_POR_JOGO]:
        shutil.rmtree(antigo)
    return destino


def restaurar(jogo: Jogo, copia: Path) -> list[Path]:
    """Volta os saves para uma cópia. Antes, guarda o estado atual (dá para desfazer)."""
    fazer_backup(jogo)
    restaurados = []
    for arquivo in sorted(copia.rglob("*")):
        if arquivo.is_file() and arquivo.name != _ASSINATURA:
            alvo = _do_backup(jogo, arquivo.relative_to(copia))
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(arquivo, alvo)
            restaurados.append(alvo)
    return restaurados
