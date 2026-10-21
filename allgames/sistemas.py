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
from xml.etree import ElementTree

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

from . import caminhos, windows
from .catalogo import Jogo

SISTEMAS = caminhos.REPO / "catalogo" / "sistemas.toml"
CORES_URL = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/{core}_libretro.so.zip"
CORES_URL_WINDOWS = "https://buildbot.libretro.com/nightly/windows/x86_64/latest/{core}_libretro.dll.zip"
WINDOWS = windows.ATIVO
ARQUIVOS_SISTEMA_URL = "https://buildbot.libretro.com/assets/system/{nome}.zip"
EDEN_RELEASES = [
    "https://git.eden-emu.dev/api/v1/repos/eden-emu/eden/releases/latest",
    "https://api.github.com/repos/eden-emulator/Releases/releases/latest",
]
# Preferência de build do Eden para Linux: a PGO é a mais rápida.
EDEN_ARQUIVOS = [r"amd64.*pgo.*\.AppImage$", r"amd64.*\.AppImage$", r"x86_64.*\.AppImage$"]
_TAGS = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
# "Jogo (USA) - Copy (12) - Copy - Copy": cópias que cartões de "15 mil jogos" trazem para inflar a contagem.
_COPIA = re.compile(r"(\s*-\s*Copy(\s*\(\d+\))?)+$", re.I)


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
    # No Windows: exe ("retroarch" = o RetroArch do winget) e, para baixar sozinho,
    # releases (páginas de versões) e arquivos (nomes do zip para Windows).
    windows: dict = field(default_factory=dict)


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
    if WINDOWS:
        return emuladores_dir() / "retroarch" / "cores"
    return Path.home() / ".var/app/org.libretro.RetroArch/config/retroarch/cores"


def arquivo_core(core: str) -> str:
    return f"{core}_libretro.dll" if WINDOWS else f"{core}_libretro.so"


def programa_windows(emulador: Emulador) -> Path | None:
    """O executável do emulador no Windows, se já estiver instalado."""
    exe = emulador.windows.get("exe")
    if not exe:
        return None
    if exe == "retroarch":
        return windows.retroarch()
    return windows.exe_baixado(emuladores_dir() / emulador.chave, exe)


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
    # A BIOS que fica junto das ROMs (o neogeo.zip do Neo Geo) não é um jogo.
    bios = {b.split()[0].lower() for b in sistema.bios}
    encontrados = []
    for pasta in pastas_do_sistema(sistema):
        arquivos = [a for a in _arquivos(pasta) if a.suffix.lower() in extensoes and a.name.lower() not in bios]
        nas_playlists = set()
        for playlist in (a for a in arquivos if a.suffix.lower() == ".m3u"):
            for linha in playlist.read_text(errors="replace").splitlines():
                if linha.strip() and not linha.startswith("#"):
                    nas_playlists.add((playlist.parent / linha.strip()).resolve())
        encontrados += [a for a in arquivos if a.resolve() not in nas_playlists] if nas_playlists else arquivos
    return _sem_repetidos(encontrados)


def _sem_repetidos(arquivos: list[Path]) -> list[Path]:
    """Esconde o mesmo jogo repetido: "Jogo - Copy (2).zip" ou o mesmo arquivo em duas pastas.

    Só some o arquivo de mesmo nome (sem o "- Copy") e mesmo tamanho de outro, então
    jogos diferentes com o mesmo nome (o "Monopoly" de GBA e o de GBC) continuam.
    Fica o original, na pasta mais rasa.
    """
    grupos: dict[tuple[str, str], list[Path]] = {}
    for arquivo in arquivos:
        grupos.setdefault((_COPIA.sub("", arquivo.stem).lower(), arquivo.suffix.lower()), []).append(arquivo)
    if all(len(grupo) == 1 for grupo in grupos.values()):
        return arquivos
    ficam = set()
    for grupo in grupos.values():
        tamanhos = set()
        for arquivo in sorted(grupo, key=lambda a: (bool(_COPIA.search(a.stem)), len(a.parts), str(a))):
            try:
                tamanho = arquivo.stat().st_size if len(grupo) > 1 else 0
            except OSError:
                continue
            if tamanho not in tamanhos:
                tamanhos.add(tamanho)
                ficam.add(arquivo)
    return [a for a in arquivos if a in ficam]


def nome_bonito(arquivo: Path) -> str:
    """'Super Mario World (USA) [!] - Copy.sfc' -> 'Super Mario World'."""
    return _TAGS.sub("", _COPIA.sub("", arquivo.stem)).strip() or arquivo.stem


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
    if WINDOWS:
        if not emulador.windows:
            return False, f"o {emulador.nome} ainda não roda no Windows"
        if not programa_windows(emulador):
            return False, f"instale o {emulador.nome}"
    elif emulador.appimage:
        if appimage(emulador):
            return True, ""
        return False, f"coloque o AppImage em {emuladores_dir() / emulador.appimage}"
    elif not flatpak_instalado(emulador.flatpak):
        return False, f"instale o {emulador.nome}"
    if sistema and sistema.core and not (cores_dir() / arquivo_core(sistema.core)).exists():
        return False, f"instale o core {sistema.core} do RetroArch"
    return True, ""


# ------------------------------------------------------------------ jogos


def _resolver_saves(padroes: list[str], rom: Path) -> list[str]:
    return [
        p.replace("{pasta_rom}", glob.escape(str(rom.parent))).replace("{nome}", glob.escape(rom.stem)) for p in padroes
    ]


# Pastas onde o EmulationStation (ArkOS, R36S) guarda as imagens baixadas pelo scraper.
_PASTAS_DE_IMAGENS = {"downloaded_images", "boxart", "boxarts", "images", "image", "covers", "media", "snap", "snaps"}
_EXTENSOES_DE_IMAGEM = {".png", ".jpg", ".jpeg"}
_cache_es: dict[Path, tuple[tuple, tuple[dict, dict]]] = {}


def _caminho_es(pasta: Path, caminho: str) -> Path | None:
    """Caminho de um gamelist.xml: './x.zip' ou '/roms/snes/x.zip' (no cartão do R36S) -> pasta/x.zip."""
    caminho = caminho.strip()
    if not caminho:
        return None
    if caminho.startswith("/"):
        _, achou, resto = caminho.partition(f"/{pasta.name}/")
        return pasta / resto if achou else Path(caminho)
    return pasta / caminho.removeprefix("./")


def do_emulationstation(pasta: Path) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    """O que o EmulationStation do ArkOS já sabia de cada ROM: nome e imagem.

    Devolve ({rom relativa à pasta, em minúsculas: (nome, imagem)}, {nome do arquivo de
    imagem, em minúsculas: imagem}), lidos do gamelist.xml (e do .old que o ArkOS deixa)
    e das pastas de imagens do scraper. Fica em cache até esses arquivos mudarem.
    """
    xmls = [pasta / "gamelist.xml", pasta / "gamelist.xml.old"]
    try:
        pastas_img = [p for p in pasta.iterdir() if p.is_dir() and p.name.lower() in _PASTAS_DE_IMAGENS]
    except OSError:
        return {}, {}
    assinatura = tuple(p.stat().st_mtime if p.exists() else 0 for p in [*xmls, *pastas_img])
    if pasta in _cache_es and _cache_es[pasta][0] == assinatura:
        return _cache_es[pasta][1]
    imagens: dict[str, str] = {}
    for sub in pastas_img:
        for arquivo in sorted(sub.rglob("*")):
            if arquivo.suffix.lower() in _EXTENSOES_DE_IMAGEM:
                imagens.setdefault(re.sub(r"-(image|thumb|boxart)$", "", arquivo.stem.lower()), str(arquivo))
    jogos_es: dict[str, tuple[str, str]] = {}
    for xml in xmls:
        try:
            raiz = ElementTree.parse(xml).getroot()
        except (OSError, ElementTree.ParseError):
            continue
        for jogo in raiz.iter("game"):
            rom = _caminho_es(pasta, jogo.findtext("path") or "")
            if not rom or not rom.is_relative_to(pasta):
                continue
            chave = rom.relative_to(pasta).as_posix().lower()
            if chave in jogos_es:
                continue
            imagem = _caminho_es(pasta, jogo.findtext("image") or "")
            jogos_es[chave] = (
                (jogo.findtext("name") or "").strip(),
                str(imagem) if imagem and imagem.suffix.lower() in _EXTENSOES_DE_IMAGEM and imagem.is_file() else "",
            )
    _cache_es[pasta] = (assinatura, (jogos_es, imagens))
    return jogos_es, imagens


def jogos(dados: tuple[dict[str, Emulador], list[Sistema]] | None = None) -> list[Jogo]:
    emuladores, sistemas = dados or carregar()
    raiz = roms_dir()
    lista = []
    for sistema in sistemas:
        arquivos = roms(sistema)
        if not arquivos:
            continue
        emulador = emuladores[sistema.emulador]
        esta_pronto, falta = pronto(emulador, sistema)
        pastas = pastas_do_sistema(sistema)
        es = {pasta: do_emulationstation(pasta) for pasta in pastas}
        for rom in arquivos:
            relativo = rom.relative_to(raiz).as_posix()
            pasta = next(p for p in pastas if rom.is_relative_to(p))
            jogos_es, imagens = es[pasta]
            nome_es, capa_local = jogos_es.get(rom.relative_to(pasta).as_posix().lower(), ("", ""))
            capa_local = capa_local or imagens.get(rom.stem.lower(), "")
            lista.append(
                Jogo(
                    id=f"rom:{relativo}",
                    nome=_TAGS.sub("", nome_es).strip() or nome_bonito(rom),
                    plataforma=sistema.nome,
                    tipo="emulador",
                    colecao=sistema.nome,
                    descricao=f"{rom.name} · {emulador.nome}",
                    controles=sistema.controles,
                    saves=_resolver_saves(emulador.saves, rom),
                    capa=f"{sistema.libretro}/{_COPIA.sub('', rom.stem)}" if sistema.libretro else "",
                    origem="rom",
                    situacao=esta_pronto,
                    acoes=["jogar"] if esta_pronto else ["instalar"],
                    extra={
                        "sistema": sistema.id,
                        "rom": str(rom),
                        "falta": falta,
                        "aviso": emulador.aviso,
                        "combo_sair": emulador.combo_sair,
                        "nome_es": nome_es,
                        "capa_local": capa_local,
                    },
                )
            )
    return lista


# Opções de core que o AllGames garante; as outras ficam como você deixar no menu do RetroArch.
OPCOES_DOS_CORES = {
    # N64 em Vulkan (ParaLLEl-RDP): o GLideN64 pede OpenGL, que no Docker roda pela CPU.
    "mupen64plus-rdp-plugin": "parallel",
    "mupen64plus-rsp-plugin": "parallel",
}


def _opcoes_dos_cores(pasta: Path) -> Path:
    """Arquivo de opções dos cores, com as do AllGames acrescentadas só se ainda não existirem."""
    arquivo = pasta / "opcoes-dos-cores.cfg"
    linhas = arquivo.read_text().splitlines() if arquivo.exists() else []
    existentes = {linha.partition("=")[0].strip() for linha in linhas if "=" in linha}
    novas = [f'{chave} = "{valor}"' for chave, valor in OPCOES_DOS_CORES.items() if chave not in existentes]
    if novas:
        arquivo.write_text("".join(f"{linha}\n" for linha in linhas + novas))
    return arquivo


# O controle que o Sunshine cria para o Moonlight diz ser de Xbox 360 (045e:028e), mas numera os
# botões como o de Xbox via Bluetooth: X=3, Y=4, LB=6, RB=7, Select=10, Start=11 (o kernel lista
# BTN_C e BTN_Z, que ele não tem). O perfil do Xbox 360 comum do RetroArch espera X=2, Y=3...
# e aí o quadrado do PlayStation, o Start e o Select+Start para sair não funcionam.
PERFIL_SUNSHINE = """input_driver = "udev"
input_device = "Sunshine (libvirtualhid) X-Box 360 Controller"
input_device_display_name = "Controle do Moonlight"
input_vendor_id = "1118"
input_product_id = "654"
input_b_btn = "0"
input_a_btn = "1"
input_y_btn = "3"
input_x_btn = "4"
input_l_btn = "6"
input_r_btn = "7"
input_select_btn = "10"
input_start_btn = "11"
input_l3_btn = "13"
input_r3_btn = "14"
input_up_btn = "h0up"
input_down_btn = "h0down"
input_left_btn = "h0left"
input_right_btn = "h0right"
input_l2_axis = "+2"
input_r2_axis = "+5"
input_l_x_plus_axis = "+0"
input_l_x_minus_axis = "-0"
input_l_y_plus_axis = "+1"
input_l_y_minus_axis = "-1"
input_r_x_plus_axis = "+3"
input_r_x_minus_axis = "-3"
input_r_y_plus_axis = "+4"
input_r_y_minus_axis = "-4"
"""
_PERFIS_DO_FLATPAK = "app/org.libretro.RetroArch/current/active/files/share/libretro/autoconfig"


def _perfis_de_controle(pasta: Path) -> Path:
    """Perfis de controle do RetroArch: os que vêm com ele e o do controle do Moonlight."""
    destino = pasta / "autoconfig"
    udev = destino / "udev"
    udev.mkdir(parents=True, exist_ok=True)
    raizes = (Path.home() / ".local/share/flatpak", Path("/var/lib/flatpak"))
    origem = next((r / _PERFIS_DO_FLATPAK for r in raizes if (r / _PERFIS_DO_FLATPAK / "udev").is_dir()), None)
    if origem:
        for perfil in (origem / "udev").glob("*.cfg"):
            if not (udev / perfil.name).exists():
                shutil.copyfile(perfil, udev / perfil.name)
    (udev / "Sunshine X-Box 360 (Moonlight).cfg").write_text(PERFIL_SUNSHINE)
    return destino


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
        # Vulkan usa a placa de vídeo dentro do Flatpak também no Docker: lá o OpenGL do
        # RetroArch cai na renderização pela CPU (llvmpipe) com placa NVIDIA.
        "video_driver": "vulkan",
        "global_core_options": "true",
        "core_options_path": str(_opcoes_dos_cores(arquivo.parent)),
        "pause_nonactive": "false",
    }
    if not WINDOWS:
        # No Windows o Sunshine cria um controle XInput comum; no Linux ele precisa do perfil próprio.
        opcoes["joypad_autoconfig_dir"] = str(_perfis_de_controle(arquivo.parent))
    arquivo.write_text("".join(f'{chave} = "{valor}"\n' for chave, valor in opcoes.items()))
    return arquivo


def comando(jogo: Jogo, dados: tuple[dict[str, Emulador], list[Sistema]] | None = None) -> list[str]:
    emuladores, sistemas = dados or carregar()
    sistema = next(s for s in sistemas if s.id == jogo.extra["sistema"])
    emulador = emuladores[sistema.emulador]
    rom = Path(jogo.extra["rom"])

    modelo = emulador.comando
    if WINDOWS:
        exe = programa_windows(emulador)
        if not exe:
            raise RuntimeError(f"o {emulador.nome} não está instalado: rode allgames emuladores instalar")
        programa = [str(exe)]
    elif emulador.appimage:
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
        "{core}": str(cores_dir() / arquivo_core(sistema.core)),
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
    destino = cores_dir() / arquivo_core(core)
    if destino.exists():
        return
    print(f"  baixando o core {core}")
    url = (CORES_URL_WINDOWS if WINDOWS else CORES_URL).format(core=core)
    with zipfile.ZipFile(io.BytesIO(_baixar(url))) as pacote:
        dados = pacote.read(arquivo_core(core))
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
                        if antigo != destino and "eden" in antigo.name.lower():
                            antigo.unlink()
                return destino
        erros.append(f"{api}: nenhum AppImage para Linux na última versão")
    raise RuntimeError("não consegui baixar o Eden: " + "; ".join(erros))


def preparar_switch() -> list[str]:
    """Instala no Eden as chaves e o firmware que estão em roms/bios/switch."""
    origem = bios_dir() / "switch"
    feito = []
    if WINDOWS:
        dados_eden = windows.appdata() / "eden"
        pastas_chaves = [dados_eden / "keys"]
    else:
        dados_eden = Path.home() / ".local/share/eden"
        pastas_chaves = [dados_eden / "keys", Path.home() / ".config/eden/keys"]
    for nome in ("prod.keys", "title.keys"):
        chave = origem / nome
        if chave.exists():
            for pasta in pastas_chaves:
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
    if WINDOWS:
        config = windows.appdata() / "xemu/xemu/xemu.toml"
    else:
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


def _instalar_no_windows(sistema: Sistema, emulador: Emulador, avisos: list[str]) -> bool:
    """Prepara o emulador no Windows. Devolve se é o RetroArch (aí ainda faltam os cores)."""
    if emulador.windows.get("exe") == "retroarch":
        if windows.retroarch():
            return True
        avisos.append(f"{sistema.nome}: instale o RetroArch (o scripts/instalar-windows.ps1 faz isso)")
        return False
    if emulador.windows.get("releases"):
        if not programa_windows(emulador):
            pasta = emuladores_dir() / emulador.chave
            windows.baixar_zip(emulador.windows["releases"], emulador.windows.get("arquivos", []), pasta)
        if sistema.id == "switch" and not (bios_dir() / "switch/prod.keys").exists():
            avisos.append(f"{sistema.nome}: {emulador.aviso}")
        return False
    avisos.append(f"{sistema.nome}: o {emulador.nome} ainda não roda no Windows")
    return False


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
            if WINDOWS:
                if not _instalar_no_windows(sistema, emulador, avisos):
                    continue
            elif emulador.appimage:
                pasta = emuladores_dir() / emulador.appimage
                pasta.mkdir(parents=True, exist_ok=True)
                atual = appimage(emulador)
                # Atualiza o Eden, mas respeita outro emulador que você tenha colocado na pasta.
                if emulador.baixar == "eden" and (not atual or "eden" in atual.name.lower()):
                    _baixar_eden(pasta)
                elif not atual:
                    avisos.append(f"{sistema.nome}: {emulador.aviso}")
                if sistema.id == "switch" and not (bios_dir() / "switch/prod.keys").exists():
                    avisos.append(f"{sistema.nome}: {emulador.aviso}")
                continue
            else:
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
