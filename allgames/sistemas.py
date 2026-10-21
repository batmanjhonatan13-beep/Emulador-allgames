"""ROMs e emuladores no estilo do ArkOS/R36S.

Cada console tem uma pasta em ~/AllGames/roms/<sistema>. Toda ROM colocada lá
vira um jogo no portal, sem precisar cadastrar nada. A BIOS fica em
~/AllGames/roms/bios, como no ArkOS, e os saves do RetroArch ficam ao lado da ROM.
"""

import glob
import io
import json
import os
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
ARQUIVOS_SISTEMA_URL = "https://buildbot.libretro.com/assets/system/{nome}.zip"
EDEN_RELEASES = [
    "https://git.eden-emu.dev/api/v1/repos/eden-emu/eden/releases/latest",
    "https://api.github.com/repos/eden-emulator/Releases/releases/latest",
]
# Preferência de build do Eden para Linux: a PGO é a mais rápida.
EDEN_ARQUIVOS = [r"amd64.*pgo.*\.AppImage$", r"amd64.*\.AppImage$", r"x86_64.*\.AppImage$"]
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
    baixar: str = ""  # "eden": o AllGames baixa o AppImage sozinho
    combo_sair: bool = False  # Select+Start segurado fecha o emulador


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
    arquivos_sistema: list[str] = field(default_factory=list)
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
    if os.environ.get("ALLGAMES_CORES"):
        return Path(os.environ["ALLGAMES_CORES"])
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
                    extra={
                        "sistema": sistema.id,
                        "rom": str(rom),
                        "falta": falta,
                        "aviso": emulador.aviso,
                        "combo_sair": emulador.combo_sair,
                    },
                )
            )
    return lista


def _config_retroarch() -> Path:
    """Configuração extra passada ao RetroArch em toda partida."""
    arquivo = emuladores_dir() / "retroarch" / "allgames.cfg"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    bios_dir().mkdir(parents=True, exist_ok=True)
    opcoes = {
        "system_directory": str(bios_dir()),
        # Saves ao lado da ROM, como no ArkOS
        "savefiles_in_content_dir": "true",
        "savestates_in_content_dir": "true",
        # Sair salva o estado e abrir continua de onde parou
        "savestate_auto_save": "true",
        "savestate_auto_load": "true",
        "autosave_interval": "10",
        # Select+Start sai (como no R36S); L3+R3 abre o menu do RetroArch
        "input_quit_gamepad_combo": "4",
        "input_menu_toggle_gamepad_combo": "2",
        "quit_press_twice": "false",
        "input_autodetect_enable": "true",
        "video_fullscreen": "true",
        "pause_nonactive": "false",
    }
    arquivo.write_text("".join(f'{chave} = "{valor}"\n' for chave, valor in opcoes.items()))
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
        programa = ["flatpak", "run", f"--filesystem={caminhos.base()}"]
        if roms_dir().resolve() != roms_dir():
            programa.append(f"--filesystem={roms_dir().resolve()}")  # ROMs em outro disco (ex.: Docker)
        if os.environ.get("ALLGAMES_CORES"):
            programa.append(f"--filesystem={cores_dir()}:ro")
        programa.append(emulador.flatpak)

    # Deixa o emulador pronto antes de abrir: chaves do Switch, BIOS do Xbox.
    if sistema.id == "switch":
        preparar_switch()
    elif sistema.id == "xbox":
        configurar_xemu()

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


def _baixar(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resposta:
        return resposta.read()


def _baixar_core(core: str) -> None:
    destino = cores_dir() / f"{core}_libretro.so"
    if destino.exists():
        return
    print(f"  baixando o core {core}")
    with zipfile.ZipFile(io.BytesIO(_baixar(CORES_URL.format(core=core)))) as pacote:
        dados = pacote.read(f"{core}_libretro.so")
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.write_bytes(dados)
    temporario.replace(destino)


def _baixar_arquivos_sistema(nome: str) -> None:
    """Arquivos de apoio de cores (ex.: Dolphin, PPSSPP), na pasta de BIOS."""
    marca = bios_dir() / f".{nome}.instalado"
    if marca.exists():
        return
    print(f"  baixando os arquivos de sistema {nome}")
    with zipfile.ZipFile(io.BytesIO(_baixar(ARQUIVOS_SISTEMA_URL.format(nome=nome), 300))) as pacote:
        pacote.extractall(bios_dir())
    marca.touch()


def _baixar_eden(pasta: Path) -> Path:
    """Baixa o AppImage mais recente do Eden (site oficial, ou o espelho no GitHub)."""
    erros = []
    for api in EDEN_RELEASES:
        try:
            assets = json.loads(_baixar(api, 30)).get("assets", [])
        except (OSError, ValueError) as erro:
            erros.append(f"{api}: {erro}")
            continue
        for padrao in EDEN_ARQUIVOS:
            escolhido = next((a for a in assets if re.search(padrao, a.get("name", ""), re.I)), None)
            if escolhido:
                destino = pasta / escolhido["name"]
                if not destino.exists():
                    print(f"  baixando {escolhido['name']}")
                    temporario = destino.with_suffix(".tmp")
                    temporario.write_bytes(_baixar(escolhido["browser_download_url"], 600))
                    temporario.chmod(0o755)
                    temporario.replace(destino)
                    for antigo in pasta.glob("*.AppImage"):
                        if antigo != destino:
                            antigo.unlink()
                return destino
        erros.append(f"{api}: nenhum AppImage para Linux na última versão")
    raise RuntimeError("não consegui baixar o Eden: " + "; ".join(erros))


def preparar_switch() -> list[str]:
    """Instala no Eden as chaves e o firmware que estão em roms/bios/switch."""
    origem = bios_dir() / "switch"
    feito = []
    dados_eden = Path.home() / ".local/share/eden"
    for nome in ("prod.keys", "title.keys"):
        chave = origem / nome
        if chave.exists():
            for pasta in (dados_eden / "keys", Path.home() / ".config/eden/keys"):
                pasta.mkdir(parents=True, exist_ok=True)
                shutil.copy2(chave, pasta / nome)
            feito.append(nome)
    firmware = sorted((origem / "firmware").glob("*.nca")) if (origem / "firmware").is_dir() else []
    if firmware:
        destino = dados_eden / "nand/system/Contents/registered"
        destino.mkdir(parents=True, exist_ok=True)
        for arquivo in firmware:
            if not (destino / arquivo.name).exists():
                shutil.copy2(arquivo, destino / arquivo.name)
        feito.append(f"firmware ({len(firmware)} arquivos)")
    return feito


def _toml_simples(dados: dict, prefixo: str = "") -> str:
    """Escreve um TOML de tabelas com textos e booleanos (o suficiente para o xemu)."""
    linhas = []
    valores = {k: v for k, v in dados.items() if not isinstance(v, dict)}
    if valores and prefixo:
        linhas.append(f"[{prefixo}]")
    for chave, valor in valores.items():
        linhas.append(f"{chave} = {json.dumps(valor) if not isinstance(valor, bool) else str(valor).lower()}")
    if linhas:
        linhas.append("")
    for chave, valor in dados.items():
        if isinstance(valor, dict):
            linhas.append(_toml_simples(valor, f"{prefixo}.{chave}" if prefixo else chave))
    return "\n".join(linhas)


def configurar_xemu() -> Path | None:
    """Aponta o xemu para a BIOS, o boot ROM e o HD do Xbox em roms/bios/xbox."""
    pasta = bios_dir() / "xbox"
    if not pasta.is_dir():
        return None
    arquivos = {p.name.lower(): p for p in pasta.iterdir() if p.is_file()}
    bootrom = next((p for n, p in arquivos.items() if n.startswith("mcpx") and n.endswith(".bin")), None)
    hd = next((p for n, p in arquivos.items() if n.endswith(".qcow2")), None)
    eeprom = next((p for n, p in arquivos.items() if "eeprom" in n), None)
    flash = next(
        (p for n, p in arquivos.items() if n.endswith(".bin") and p not in (bootrom, eeprom)),
        None,
    )
    config = Path.home() / ".var/app/app.xemu.xemu/data/xemu/xemu/xemu.toml"
    try:
        atual = tomllib.loads(config.read_text())
    except (OSError, ValueError):
        atual = {}
    arquivos_sys = atual.setdefault("sys", {}).setdefault("files", {})
    for chave, caminho in (
        ("bootrom_path", bootrom),
        ("flashrom_path", flash),
        ("hdd_path", hd),
        ("eeprom_path", eeprom),
    ):
        if caminho:
            arquivos_sys[chave] = str(caminho)
    atual.setdefault("general", {})["show_welcome"] = False
    atual.setdefault("display", {}).setdefault("window", {})["fullscreen_on_startup"] = True
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(_toml_simples(atual))
    return config


def instalar_flatpak(app: str) -> None:
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


def instalar(alvos: list[str], dados=None, todos: bool = False) -> list[str]:
    """Instala emuladores (e cores) pelos ids de sistema ou chaves de emulador.

    Sem alvos, instala o que os sistemas que já têm ROMs precisam (ou todos, com
    `todos`). Devolve avisos para o que precisa ser feito à mão.
    """
    emuladores, sistemas = dados or carregar()
    if todos:
        escolhidos = list(sistemas)
    elif alvos:
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
        try:
            if emulador.appimage:
                pasta = emuladores_dir() / emulador.appimage
                pasta.mkdir(parents=True, exist_ok=True)
                if emulador.baixar == "eden":
                    _baixar_eden(pasta)
                elif not appimage(emulador):
                    avisos.append(f"{sistema.nome}: {emulador.aviso}")
                if sistema.id == "switch" and not (bios_dir() / "switch/prod.keys").exists():
                    avisos.append(f"{sistema.nome}: {emulador.aviso}")
                continue
            instalar_flatpak(emulador.flatpak)
            if sistema.core:
                _baixar_core(sistema.core)
            for nome in sistema.arquivos_sistema:
                _baixar_arquivos_sistema(nome)
        except (OSError, RuntimeError, zipfile.BadZipFile, subprocess.CalledProcessError) as erro:
            avisos.append(f"{sistema.nome}: falhou ({erro})")
    return list(dict.fromkeys(avisos))


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
