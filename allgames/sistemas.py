"""ROMs e emuladores no estilo do ArkOS/R36S.

Cada console tem uma pasta em ~/AllGames/roms/<sistema>. Toda ROM colocada lá
vira um jogo no portal, sem precisar cadastrar nada. A BIOS fica em
~/AllGames/roms/bios, como no ArkOS, e os saves do RetroArch ficam ao lado da ROM.
"""

import glob
import io
import re
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

from . import caminhos
from .catalogo import Jogo

SISTEMAS = caminhos.REPO / "catalogo" / "sistemas.toml"
CORES_URL = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/{core}_libretro.so.zip"
_TAGS = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")


@dataclass
class Emulador:
    chave: str
    nome: str
    comando: list[str]
    flatpak: str = ""
    appimage: str = ""
    saves: list[str] = field(default_factory=list)
    aviso: str = ""
    alternativas: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Sistema:
    id: str
    nome: str
    extensoes: list[str]
    emulador: str
    pastas: list[str] = field(default_factory=list)
    core: str = ""
    libretro: str = ""
    bios: list[str] = field(default_factory=list)
    controles: list[str] = field(default_factory=lambda: ["controle"])


def carregar(arquivo: Path = SISTEMAS) -> tuple[dict[str, Emulador], list[Sistema]]:
    with open(arquivo, "rb") as f:
        dados = tomllib.load(f)
    emuladores = {chave: Emulador(chave=chave, **valores) for chave, valores in dados.get("emulador", {}).items()}
    sistemas = [Sistema(**s) for s in dados.get("sistema", [])]
    for sistema in sistemas:
        if sistema.emulador not in emuladores:
            raise ValueError(f"{arquivo}: sistema {sistema.id} usa o emulador desconhecido {sistema.emulador!r}")
    return emuladores, sistemas


# ------------------------------------------------------------------ pastas


def roms_dir() -> Path:
    return caminhos.base() / "roms"


def bios_dir() -> Path:
    return roms_dir() / "bios"


def emuladores_dir() -> Path:
    return caminhos.base() / "emuladores"


def cores_dir() -> Path:
    return Path.home() / ".var/app/org.libretro.RetroArch/config/retroarch/cores"


def pastas_do_sistema(sistema: Sistema) -> list[Path]:
    """Pastas existentes do sistema, aceitando os nomes alternativos e maiúsculas."""
    if not roms_dir().is_dir():
        return []
    nomes = {n.lower() for n in [sistema.id, *sistema.pastas]}
    return sorted(p for p in roms_dir().iterdir() if p.is_dir() and p.name.lower() in nomes)


def _arquivos(pasta: Path, profundidade: int = 2):
    for item in sorted(pasta.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir() and profundidade > 1:
            yield from _arquivos(item, profundidade - 1)
        elif item.is_file():
            yield item


def roms(sistema: Sistema) -> list[Path]:
    """ROMs do sistema. Discos citados numa playlist .m3u ficam escondidos atrás dela."""
    extensoes = {f".{e.lower()}" for e in sistema.extensoes}
    encontrados = []
    for pasta in pastas_do_sistema(sistema):
        arquivos = [a for a in _arquivos(pasta) if a.suffix.lower() in extensoes]
        nas_playlists = set()
        for playlist in (a for a in arquivos if a.suffix.lower() == ".m3u"):
            for linha in playlist.read_text(errors="replace").splitlines():
                if linha.strip() and not linha.startswith("#"):
                    nas_playlists.add((playlist.parent / linha.strip()).resolve())
        encontrados += [a for a in arquivos if a.resolve() not in nas_playlists]
    return encontrados


def nome_bonito(arquivo: Path) -> str:
    """'Super Mario World (USA) [!].sfc' -> 'Super Mario World'."""
    return _TAGS.sub("", arquivo.stem).strip() or arquivo.stem


# ------------------------------------------------------------------ emuladores instalados


def flatpak_instalado(app: str) -> bool:
    return any(
        (raiz / app / "current").exists()
        for raiz in (Path.home() / ".local/share/flatpak/app", Path("/var/lib/flatpak/app"))
    )


def appimage(emulador: Emulador) -> Path | None:
    pasta = emuladores_dir() / emulador.appimage
    if not pasta.is_dir():
        return None
    candidatos = sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() == ".appimage")
    return candidatos[-1] if candidatos else None


def pronto(emulador: Emulador, sistema: Sistema | None = None) -> tuple[bool, str]:
    """(está pronto?, o que falta)."""
    if emulador.appimage:
        if appimage(emulador):
            return True, ""
        return False, f"coloque o AppImage em {emuladores_dir() / emulador.appimage}"
    if not flatpak_instalado(emulador.flatpak):
        return False, f"instale o {emulador.nome}"
    if sistema and sistema.core and not (cores_dir() / f"{sistema.core}_libretro.so").exists():
        return False, f"instale o core {sistema.core} do RetroArch"
    return True, ""


# ------------------------------------------------------------------ jogos


def _resolver_saves(padroes: list[str], rom: Path) -> list[str]:
    return [
        p.replace("{pasta_rom}", glob.escape(str(rom.parent))).replace("{nome}", glob.escape(rom.stem)) for p in padroes
    ]


def jogos(dados: tuple[dict[str, Emulador], list[Sistema]] | None = None) -> list[Jogo]:
    emuladores, sistemas = dados or carregar()
    lista = []
    for sistema in sistemas:
        arquivos = roms(sistema)
        if not arquivos:
            continue
        emulador = emuladores[sistema.emulador]
        esta_pronto, falta = pronto(emulador, sistema)
        for rom in arquivos:
            relativo = rom.relative_to(roms_dir()).as_posix()
            lista.append(
                Jogo(
                    id=f"rom:{relativo}",
                    nome=nome_bonito(rom),
                    plataforma=sistema.nome,
                    tipo="emulador",
                    colecao=sistema.nome,
                    descricao=f"{rom.name} · {emulador.nome}",
                    controles=sistema.controles,
                    saves=_resolver_saves(emulador.saves, rom),
                    capa=f"{sistema.libretro}/{rom.stem}" if sistema.libretro else "",
                    origem="rom",
                    situacao=esta_pronto,
                    acoes=["jogar"] if esta_pronto else ["instalar"],
                    extra={"sistema": sistema.id, "rom": str(rom), "falta": falta, "aviso": emulador.aviso},
                )
            )
    return lista


def _config_retroarch() -> Path:
    """Configuração extra passada ao RetroArch em toda partida."""
    arquivo = emuladores_dir() / "retroarch" / "allgames.cfg"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    bios_dir().mkdir(parents=True, exist_ok=True)
    arquivo.write_text(
        f'system_directory = "{bios_dir()}"\n'
        'savefiles_in_content_dir = "true"\n'
        'savestates_in_content_dir = "true"\n'
        'video_fullscreen = "true"\n'
        'pause_nonactive = "false"\n'
    )
    return arquivo


def comando(jogo: Jogo, dados: tuple[dict[str, Emulador], list[Sistema]] | None = None) -> list[str]:
    emuladores, sistemas = dados or carregar()
    sistema = next(s for s in sistemas if s.id == jogo.extra["sistema"])
    emulador = emuladores[sistema.emulador]
    rom = Path(jogo.extra["rom"])

    modelo = emulador.comando
    if emulador.appimage:
        arquivo = appimage(emulador)
        if not arquivo:
            raise RuntimeError(f"emulador não encontrado: coloque o AppImage em {emuladores_dir() / emulador.appimage}")
        for palavra, alternativo in emulador.alternativas.items():
            if palavra.lower() in arquivo.name.lower():
                modelo = alternativo
        programa = [str(arquivo)]
    else:
        # O Flatpak roda isolado: libera a pasta do AllGames (ROMs, BIOS e saves).
        programa = ["flatpak", "run", f"--filesystem={caminhos.base()}", emulador.flatpak]

    valores = {
        "{rom}": str(rom),
        "{pasta_rom}": str(rom.parent),
        "{roms}": str(roms_dir()),
        "{bios}": str(bios_dir()),
        "{core}": str(cores_dir() / f"{sistema.core}_libretro.so"),
    }
    argv = []
    for parte in modelo:
        if parte == "{emulador}":
            argv += programa
            continue
        if "{retroarch_cfg}" in parte:
            parte = parte.replace("{retroarch_cfg}", str(_config_retroarch()))
        for marcador, valor in valores.items():
            parte = parte.replace(marcador, valor)
        argv.append(parte)
    return argv


# ------------------------------------------------------------------ instalação


def _baixar_core(core: str) -> None:
    destino = cores_dir() / f"{core}_libretro.so"
    if destino.exists():
        return
    print(f"  baixando o core {core}")
    with urllib.request.urlopen(CORES_URL.format(core=core), timeout=120) as resposta:
        conteudo = resposta.read()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
        dados = pacote.read(f"{core}_libretro.so")
    temporario = destino.with_suffix(".tmp")
    temporario.write_bytes(dados)
    temporario.replace(destino)


def _instalar_flatpak(app: str) -> None:
    if flatpak_instalado(app):
        return
    if not shutil.which("flatpak"):
        raise RuntimeError("o Flatpak não está instalado; rode scripts/instalar-host.sh")
    print(f"  instalando {app} do Flathub")
    subprocess.run(
        [
            "flatpak",
            "remote-add",
            "--user",
            "--if-not-exists",
            "flathub",
            "https://dl.flathub.org/repo/flathub.flatpakrepo",
        ],
        check=True,
    )
    subprocess.run(["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", app], check=True)


def instalar(alvos: list[str], dados=None) -> list[str]:
    """Instala emuladores (e cores) pelos ids de sistema ou chaves de emulador.

    Sem alvos, instala o que os sistemas que já têm ROMs precisam. Devolve avisos
    para o que precisa ser feito à mão (AppImages).
    """
    emuladores, sistemas = dados or carregar()
    if alvos:
        escolhidos = [s for s in sistemas if s.id in alvos or s.emulador in alvos]
        desconhecidos = set(alvos) - {s.id for s in sistemas} - set(emuladores)
        if desconhecidos:
            raise ValueError(f"não conheço: {', '.join(sorted(desconhecidos))} (veja: allgames emuladores)")
    else:
        escolhidos = [s for s in sistemas if roms(s)]
    avisos = []
    for sistema in escolhidos:
        emulador = emuladores[sistema.emulador]
        print(f"{sistema.nome}: {emulador.nome}")
        if emulador.appimage:
            if not appimage(emulador):
                (emuladores_dir() / emulador.appimage).mkdir(parents=True, exist_ok=True)
                avisos.append(f"{sistema.nome}: {emulador.aviso}")
            continue
        _instalar_flatpak(emulador.flatpak)
        if sistema.core:
            _baixar_core(sistema.core)
    return avisos


def preparar_pastas(dados=None) -> list[Path]:
    """Cria a estrutura de pastas do ArkOS com um LEIA-ME em cada uma."""
    emuladores, sistemas = dados or carregar()
    criadas = []
    for sistema in sistemas:
        if pastas_do_sistema(sistema):
            continue
        pasta = roms_dir() / sistema.id
        pasta.mkdir(parents=True, exist_ok=True)
        criadas.append(pasta)
        emulador = emuladores[sistema.emulador]
        linhas = [
            f"{sistema.nome}",
            f"Coloque aqui as ROMs ({', '.join('.' + e for e in sistema.extensoes)}).",
            f"Emulador: {emulador.nome}.",
        ]
        if sistema.bios:
            linhas.append(f"BIOS do seu console, em {bios_dir()}: {', '.join(sistema.bios)}.")
        if emulador.aviso:
            linhas.append(emulador.aviso)
        (pasta / "LEIA-ME.txt").write_text("\n".join(linhas) + "\n")
    bios_dir().mkdir(parents=True, exist_ok=True)
    for emulador in emuladores.values():
        if emulador.appimage:
            (emuladores_dir() / emulador.appimage).mkdir(parents=True, exist_ok=True)
    return criadas
