"""Leitura do catalogo/jogos.toml e verificação dos arquivos originais."""

import fnmatch
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

from . import caminhos

TIPOS = {"port", "recomp", "emulador"}


class ErroCatalogo(Exception):
    pass


@dataclass
class Original:
    arquivo: str
    descricao: str = ""
    sha1: list[str] = field(default_factory=list)
    opcional: bool = False

    def localizar(self, pasta: Path) -> Path | None:
        """Primeiro arquivo da pasta que bate com o padrão, sem diferenciar maiúsculas."""
        if not pasta.is_dir():
            return None
        padrao = self.arquivo.lower()
        for caminho in sorted(pasta.iterdir()):
            if caminho.is_file() and fnmatch.fnmatchcase(caminho.name.lower(), padrao):
                return caminho
        return None


@dataclass
class Jogo:
    id: str
    nome: str
    plataforma: str
    tipo: str
    decomp: str = ""
    projeto: str = ""
    capa: str = ""
    originais: list[Original] = field(default_factory=list)

    @property
    def receita(self) -> Path:
        return caminhos.RECEITAS / f"{self.id}.sh"

    @property
    def pasta(self) -> Path:
        return caminhos.jogos() / self.id

    @property
    def instalado(self) -> bool:
        return (self.pasta / ".instalado").exists()


def carregar(arquivo: Path = caminhos.CATALOGO) -> list[Jogo]:
    with open(arquivo, "rb") as f:
        dados = tomllib.load(f)

    jogos = []
    vistos = set()
    for item in dados.get("jogo", []):
        try:
            originais = [Original(**o) for o in item.pop("originais", [])]
            jogo = Jogo(**item, originais=originais)
        except TypeError as e:
            raise ErroCatalogo(f"{arquivo}: entrada inválida {item.get('id', '?')!r}: {e}") from None
        if jogo.id in vistos:
            raise ErroCatalogo(f"{arquivo}: id repetido {jogo.id!r}")
        if jogo.tipo not in TIPOS:
            raise ErroCatalogo(f"{arquivo}: {jogo.id}: tipo {jogo.tipo!r} (use {', '.join(sorted(TIPOS))})")
        vistos.add(jogo.id)
        jogos.append(jogo)
    return jogos


def buscar(jogos: list[Jogo], id_: str) -> Jogo:
    for jogo in jogos:
        if jogo.id == id_:
            return jogo
    raise ErroCatalogo(f"jogo {id_!r} não está no catálogo (veja: allgames listar)")


def sha1(caminho: Path) -> str:
    h = hashlib.sha1()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


@dataclass
class Verificacao:
    original: Original
    caminho: Path | None
    problema: str = ""

    @property
    def ok(self) -> bool:
        return not self.problema


def verificar(jogo: Jogo, conferir_hash: bool = True) -> list[Verificacao]:
    """Confere cada arquivo original do jogo. Arquivos opcionais ausentes não são problema."""
    pasta = caminhos.originais()
    resultado = []
    for original in jogo.originais:
        caminho = original.localizar(pasta)
        problema = ""
        if caminho is None:
            if not original.opcional:
                problema = f"falta {original.arquivo} em {pasta}"
        elif conferir_hash and original.sha1:
            if sha1(caminho).lower() not in {h.lower() for h in original.sha1}:
                problema = f"{caminho.name} não é a versão esperada (SHA-1 diferente)"
        resultado.append(Verificacao(original, caminho, problema))
    return resultado
