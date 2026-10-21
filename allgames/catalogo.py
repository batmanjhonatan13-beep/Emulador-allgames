"""Leitura do catalogo/jogos.toml e verificação dos arquivos originais."""

import fnmatch
import hashlib
import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

from . import caminhos

TIPOS = {"port", "recomp", "emulador", "pc"}
# "controle": precisa de controle (Bluetooth ou o controle virtual na tela do Moonlight)
# "toque": dá para jogar tocando direto na tela, como um mouse
CONTROLES = {"controle", "toque"}


class ErroCatalogo(Exception):
    pass


@dataclass
class Original:
    # Padrão do nome do arquivo; aceita curingas e alternativas separadas por "|".
    arquivo: str
    descricao: str = ""
    sha1: list[str] = field(default_factory=list)
    opcional: bool = False

    def candidatos(self, pasta: Path) -> list[Path]:
        if not pasta.is_dir():
            return []
        padroes = [p.strip().lower() for p in self.arquivo.split("|")]
        return [
            caminho
            for caminho in sorted(pasta.iterdir())
            if caminho.is_file() and any(fnmatch.fnmatchcase(caminho.name.lower(), p) for p in padroes)
        ]

    def localizar(self, pasta: Path) -> Path | None:
        """Arquivo que bate com o padrão e, se houver `sha1`, com um dos hashes.

        Com hash, o nome do arquivo não importa: "*.gba" + o SHA-1 do Emerald acha
        o Emerald no meio das outras ROMs de GBA.
        """
        aceitos = {h.lower() for h in self.sha1}
        for caminho in self.candidatos(pasta):
            if not aceitos or sha1(caminho) in aceitos:
                return caminho
        return None


@dataclass
class Jogo:
    id: str
    nome: str
    plataforma: str
    tipo: str
    receita: str = ""  # receitas/<receita>.sh; vazio = receitas/<id>.sh
    colecao: str = ""
    descricao: str = ""
    controles: list[str] = field(default_factory=lambda: ["controle"])
    saves: list[str] = field(default_factory=list)
    decomp: str = ""
    projeto: str = ""
    capa: str = ""
    originais: list[Original] = field(default_factory=list)
    # Preenchidos pelo AllGames para ROMs (sistemas.py) e lojas (lojas.py):
    origem: str = "catalogo"  # catalogo | rom | steam | heroic | portmaster
    acoes: list[str] = field(default_factory=lambda: ["jogar"])
    capa_url: str = ""
    capa_alternativa: str = ""
    situacao: bool | None = None  # instalado ou não, quando não depende de .instalado
    extra: dict = field(default_factory=dict)

    @property
    def arquivo_receita(self) -> Path:
        return caminhos.RECEITAS / f"{self.receita or self.id}.sh"

    @property
    def pasta(self) -> Path:
        # "rom:snes/Jogo.sfc" -> jogos/rom/snes/Jogo.sfc
        return caminhos.jogos() / self.id.replace(":", "/")

    @property
    def chave(self) -> str:
        """O id em forma de nome de arquivo (capas, caches)."""
        return re.sub(r"[^A-Za-z0-9._-]+", "_", self.id)

    @property
    def instalado(self) -> bool:
        if self.situacao is not None:
            return self.situacao
        return (self.pasta / ".instalado").exists()

    @property
    def jogado_em(self) -> float | None:
        marca = self.pasta / ".jogado"
        return marca.stat().st_mtime if marca.exists() else None


def carregar(arquivo: Path = caminhos.CATALOGO) -> list[Jogo]:
    with open(arquivo, "rb") as f:
        dados = tomllib.load(f)

    # [receita.<nome>] guarda valores padrão para todos os jogos que usam a receita.
    padroes = dados.get("receita", {})
    jogos = []
    vistos = set()
    for item in dados.get("jogo", []):
        item = {**padroes.get(item.get("receita", item.get("id")), {}), **item}
        try:
            originais = [Original(**o) for o in item.pop("originais", [])]
            jogo = Jogo(**item, originais=originais)
        except TypeError as e:
            raise ErroCatalogo(f"{arquivo}: entrada inválida {item.get('id', '?')!r}: {e}") from None
        if jogo.id in vistos:
            raise ErroCatalogo(f"{arquivo}: id repetido {jogo.id!r}")
        if jogo.tipo not in TIPOS:
            raise ErroCatalogo(f"{arquivo}: {jogo.id}: tipo {jogo.tipo!r} (use {', '.join(sorted(TIPOS))})")
        if not jogo.controles or set(jogo.controles) - CONTROLES:
            raise ErroCatalogo(f"{arquivo}: {jogo.id}: controles {jogo.controles} (use {', '.join(sorted(CONTROLES))})")
        vistos.add(jogo.id)
        jogos.append(jogo)
    return jogos


def buscar(jogos: list[Jogo], id_: str) -> Jogo:
    for jogo in jogos:
        if jogo.id == id_:
            return jogo
    raise ErroCatalogo(f"jogo {id_!r} não está no catálogo (veja: allgames listar)")


_cache_trava = threading.Lock()


def sha1(caminho: Path) -> str:
    """SHA-1 do arquivo, com cache (ISOs e ROMs de DS são grandes)."""
    info = caminho.stat()
    chave = str(caminho.resolve())
    marca = [info.st_size, info.st_mtime_ns]
    arquivo_cache = caminhos.base() / ".sha1-cache.json"
    with _cache_trava:
        try:
            cache = json.loads(arquivo_cache.read_text())
        except (OSError, ValueError):
            cache = {}
        if cache.get(chave, {}).get("marca") == marca:
            return cache[chave]["sha1"]
    h = hashlib.sha1()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    resultado = h.hexdigest()
    with _cache_trava:
        try:
            cache = json.loads(arquivo_cache.read_text())
        except (OSError, ValueError):
            cache = {}
        cache[chave] = {"marca": marca, "sha1": resultado}
        arquivo_cache.parent.mkdir(parents=True, exist_ok=True)
        temporario = arquivo_cache.with_suffix(".tmp")
        temporario.write_text(json.dumps(cache))
        temporario.replace(arquivo_cache)
    return resultado


@dataclass
class Verificacao:
    original: Original
    caminho: Path | None
    problema: str = ""

    @property
    def ok(self) -> bool:
        return not self.problema


def verificar(jogo: Jogo) -> list[Verificacao]:
    """Confere cada arquivo original do jogo. Arquivos opcionais ausentes não são problema."""
    pasta = caminhos.originais()
    resultado = []
    for original in jogo.originais:
        caminho = original.localizar(pasta)
        problema = ""
        if caminho is None and not original.opcional:
            if original.sha1 and original.candidatos(pasta):
                problema = f"nenhum arquivo {original.arquivo} em {pasta} é a versão esperada (SHA-1 diferente)"
            else:
                problema = f"falta {original.arquivo} em {pasta}"
        resultado.append(Verificacao(original, caminho, problema))
    return resultado
