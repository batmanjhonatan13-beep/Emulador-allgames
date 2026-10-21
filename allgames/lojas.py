"""Bibliotecas da Steam e do Heroic (Epic, GOG e Amazon) no portal.

Os jogos rodam no PC (Proton/Wine para os de Windows) e aparecem no portal com
capa, para jogar, instalar e desinstalar pelo celular:

- Steam: os instalados vêm dos arquivos da própria Steam; a biblioteca inteira
  (comprados e não instalados) vem da Web API da Steam, se você configurar a
  chave em ~/AllGames/config.toml.
- Heroic: lê a biblioteca que o Heroic já guarda depois que você entra nas
  contas Epic, GOG e Amazon. Jogos da Ubisoft comprados na Epic abrem o Ubisoft
  Connect sozinhos pelo Heroic.
"""

import json
import os
import random
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

from . import caminhos, windows
from .catalogo import Jogo
from .sistemas import flatpak_instalado

STEAM_CDN = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/{imagem}"
STEAM_API = (
    "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    "?key={chave}&steamid={steamid}&include_appinfo=1&format=json"
)
# Ferramentas que a Steam instala como "jogos" e não devem aparecer no portal.
_STEAM_FERRAMENTAS = re.compile(r"^(proton|steam linux runtime|steamworks common)|redistributable", re.I)
_HEROIC_LOJAS = {"legendary": "Epic Games", "gog": "GOG", "nile": "Amazon Games", "sideload": "Heroic"}


def configuracao() -> dict:
    arquivo = caminhos.base() / "config.toml"
    try:
        return tomllib.loads(arquivo.read_text())
    except (OSError, ValueError):
        return {}


# ------------------------------------------------------------------ processos


def _processos():
    """(pid, linha de comando, pasta atual) dos processos do usuário, menos os do próprio AllGames."""
    for pasta in Path("/proc").iterdir():
        if not pasta.name.isdigit():
            continue
        try:
            cmdline = (pasta / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            cwd = os.readlink(pasta / "cwd")
        except OSError:
            continue
        if "allgames" in cmdline:
            continue
        yield int(pasta.name), cmdline, cwd


def esperar_processo(achar, aparecer: float = 180, intervalo: float = 2) -> bool:
    """Espera um processo do jogo aparecer e depois sumir. Devolve se ele chegou a aparecer."""
    limite = time.monotonic() + aparecer
    while not any(achar(c, d) for _, c, d in _processos()):
        if time.monotonic() > limite:
            return False
        time.sleep(intervalo)
    while any(achar(c, d) for _, c, d in _processos()):
        time.sleep(intervalo)
    return True


# ------------------------------------------------------------------ Steam


def _vdf(texto: str) -> dict:
    """Leitor mínimo do formato VDF (texto) da Steam."""
    tokens = re.findall(r'"((?:[^"\\]|\\.)*)"|([{}])', texto)
    raiz: dict = {}
    pilha = [raiz]
    chave = None
    for valor, chave_ou_fecha in tokens:
        if chave_ou_fecha == "{":
            novo: dict = {}
            pilha[-1][chave] = novo
            pilha.append(novo)
            chave = None
        elif chave_ou_fecha == "}":
            pilha.pop()
        elif chave is None:
            chave = valor
        else:
            pilha[-1][chave] = re.sub(r'\\(["\\])', r"\1", valor)
            chave = None
    return raiz


def _vdf_texto(dados: dict, nivel: int = 0) -> str:
    """Escreve o formato VDF (texto) da Steam, o inverso de _vdf."""
    recuo = "\t" * nivel
    linhas = []
    for chave, valor in dados.items():
        if isinstance(valor, dict):
            linhas += [f'{recuo}"{chave}"', f"{recuo}{{", _vdf_texto(valor, nivel + 1).rstrip("\n"), f"{recuo}}}"]
        else:
            texto = str(valor).replace("\\", "\\\\").replace('"', '\\"')
            linhas.append(f'{recuo}"{chave}"\t\t"{texto}"')
    return "".join(f"{linha}\n" for linha in linhas if linha)


def registrar_biblioteca_steam(raiz: Path, rotulo: str = "Steam do PC") -> bool:
    """Acrescenta uma pasta de jogos já instalados à Steam (que precisa estar fechada).

    É como a Steam faz ao "adicionar pasta de biblioteca": no Docker, os jogos que você
    já tinha baixado na Steam do Pop!_OS aparecem sem baixar de novo. Devolve se mudou algo.
    """
    principal = Path.home() / ".local/share/Steam/steamapps/libraryfolders.vdf"
    try:
        dados = _vdf(principal.read_text(errors="replace"))
    except OSError:
        return False  # a Steam ainda não abriu nenhuma vez
    pastas = dados.setdefault("libraryfolders", {})
    if any(isinstance(p, dict) and p.get("path") == str(raiz) for p in pastas.values()):
        return False
    marcador = raiz / "libraryfolder.vdf"
    try:
        contentid = _vdf(marcador.read_text(errors="replace"))["libraryfolder"]["contentid"]
    except (OSError, KeyError, TypeError):
        contentid = str(random.getrandbits(62))
        marcador.write_text(_vdf_texto({"libraryfolder": {"contentid": contentid, "label": rotulo}}))
    apps = {}
    for manifesto in sorted((raiz / "steamapps").glob("appmanifest_*.acf")):
        app = _vdf(manifesto.read_text(errors="replace")).get("AppState", {})
        if app.get("appid"):
            apps[app["appid"]] = app.get("SizeOnDisk", "0")
    pastas[str(max((int(k) for k in pastas if k.isdigit()), default=-1) + 1)] = {
        "path": str(raiz),
        "label": rotulo,
        "contentid": contentid,
        "totalsize": "0",
        "update_clean_bytes_tally": "0",
        "time_last_update_verified": "0",
        "apps": apps,
    }
    temporario = principal.with_name(f"{principal.name}.allgames")
    temporario.write_text(_vdf_texto(dados))
    temporario.replace(principal)
    return True


def steam_raiz() -> Path | None:
    if windows.ATIVO:
        exe = windows.steam()
        return exe.parent if exe and (exe.parent / "steamapps").is_dir() else None
    for raiz in (
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam",
        Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ):
        if (raiz / "steamapps").is_dir():
            return raiz
    return None


def steam_comando() -> list[str] | None:
    if windows.ATIVO:
        exe = windows.steam()
        return [str(exe)] if exe else None
    if shutil.which("steam"):
        return ["steam"]
    if flatpak_instalado("com.valvesoftware.Steam"):
        return ["flatpak", "run", "com.valvesoftware.Steam"]
    return None


def steam_bibliotecas() -> list[Path]:
    """Pastas "steamapps" de todas as bibliotecas da Steam (inclusive outros discos)."""
    raiz = steam_raiz()
    if not raiz:
        return []
    bibliotecas = [raiz / "steamapps"]
    try:
        pastas = _vdf((raiz / "steamapps/libraryfolders.vdf").read_text(errors="replace")).get("libraryfolders", {})
        bibliotecas += [Path(p["path"]) / "steamapps" for p in pastas.values() if isinstance(p, dict) and "path" in p]
    except OSError:
        pass
    return [b for b in dict.fromkeys(bibliotecas) if b.is_dir()]


def steam_manifestos():
    """(pasta steamapps, AppState) de cada jogo que a Steam conhece, menos as ferramentas."""
    for biblioteca in steam_bibliotecas():
        for manifesto in biblioteca.glob("appmanifest_*.acf"):
            try:
                app = _vdf(manifesto.read_text(errors="replace")).get("AppState", {})
            except OSError:
                continue
            if app.get("appid") and app.get("name") and not _STEAM_FERRAMENTAS.search(app["name"]):
                yield biblioteca, app


def steam_instalados() -> dict[str, str]:
    """appid -> nome dos jogos instalados, em todas as bibliotecas da Steam."""
    # StateFlags 4 = totalmente instalado
    return {app["appid"]: app["name"] for _, app in steam_manifestos() if int(app.get("StateFlags", 0)) & 4}


def steam_biblioteca() -> dict[str, str]:
    """appid -> nome de todos os jogos da conta (precisa de chave da Web API), com cache de 6 horas."""
    steam = configuracao().get("steam", {})
    chave, steamid = steam.get("chave_api"), steam.get("steamid")
    if not (chave and steamid):
        return {}
    cache = caminhos.base() / ".cache-steam.json"
    try:
        dados = json.loads(cache.read_text())
        if time.time() - dados["quando"] < 6 * 3600:
            return dados["jogos"]
    except (OSError, ValueError, KeyError):
        pass
    try:
        url = STEAM_API.format(chave=urllib.parse.quote(chave), steamid=urllib.parse.quote(str(steamid)))
        with urllib.request.urlopen(url, timeout=20) as resposta:
            lista = json.load(resposta).get("response", {}).get("games", [])
    except (OSError, ValueError):
        return {}
    jogos = {str(j["appid"]): j.get("name", str(j["appid"])) for j in lista}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"quando": time.time(), "jogos": jogos}))
    return jogos


def steam_jogos() -> list[Jogo]:
    instalados = steam_instalados()
    todos = {**steam_biblioteca(), **instalados}
    lista = []
    for appid, nome in todos.items():
        instalado = appid in instalados
        lista.append(
            Jogo(
                id=f"steam:{appid}",
                nome=nome,
                plataforma="Steam",
                tipo="pc",
                colecao="Steam",
                descricao="Da sua biblioteca Steam. Jogos de Windows rodam pelo Proton.",
                saves=[
                    f"~/.local/share/Steam/userdata/*/{appid}/**/*",
                    f"~/.var/app/com.valvesoftware.Steam/.local/share/Steam/userdata/*/{appid}/**/*",
                ],
                origem="steam",
                situacao=instalado,
                acoes=["jogar", "desinstalar"] if instalado else ["instalar"],
                capa_url=STEAM_CDN.format(appid=appid, imagem="library_600x900.jpg"),
                capa_alternativa=STEAM_CDN.format(appid=appid, imagem="header.jpg"),
                extra={"appid": appid},
            )
        )
    return sorted(lista, key=lambda j: j.nome.lower())


# ------------------------------------------------------------------ Heroic


def heroic_raiz() -> Path | None:
    for raiz in (Path.home() / ".config/heroic", Path.home() / ".var/app/com.heroicgameslauncher.hgl/config/heroic"):
        if raiz.is_dir():
            return raiz
    return None


def heroic_comando() -> list[str] | None:
    if shutil.which("heroic"):
        return ["heroic"]
    if flatpak_instalado("com.heroicgameslauncher.hgl"):
        return ["flatpak", "run", "com.heroicgameslauncher.hgl"]
    return None


def _ler_json(arquivo: Path):
    try:
        return json.loads(arquivo.read_text())
    except (OSError, ValueError):
        return None


def _heroic_pastas_instaladas(raiz: Path) -> dict[tuple[str, str], str]:
    """(runner, app) -> pasta de instalação, dos arquivos de instalação de cada loja."""
    pastas = {}
    legendary = _ler_json(raiz / "legendaryConfig/legendary/installed.json") or {}
    for app, info in legendary.items():
        if isinstance(info, dict) and info.get("install_path"):
            pastas[("legendary", app)] = info["install_path"]
    gog = (_ler_json(raiz / "gog_store/installed.json") or {}).get("installed", [])
    for info in gog:
        if isinstance(info, dict) and info.get("appName") and info.get("install_path"):
            pastas[("gog", info["appName"])] = info["install_path"]
    nile = _ler_json(raiz / "nile_config/nile/installed.json") or []
    for info in nile if isinstance(nile, list) else []:
        if isinstance(info, dict) and info.get("id") and info.get("path"):
            pastas[("nile", info["id"])] = info["path"]
    return pastas


def heroic_jogos() -> list[Jogo]:
    raiz = heroic_raiz()
    if not raiz:
        return []
    instalados = _heroic_pastas_instaladas(raiz)
    fontes = [
        ("legendary", raiz / "store_cache/legendary_library.json", "library"),
        ("gog", raiz / "store_cache/gog_library.json", "games"),
        ("nile", raiz / "store_cache/nile_library.json", "library"),
        ("sideload", raiz / "sideload_apps/library.json", "games"),
    ]
    lista = []
    for runner, arquivo, chave in fontes:
        for info in (_ler_json(arquivo) or {}).get(chave, []) or []:
            if not isinstance(info, dict) or not info.get("app_name") or info.get("is_dlc"):
                continue
            app = info["app_name"]
            pasta = instalados.get((runner, app)) or (info.get("install") or {}).get("install_path", "")
            instalado = bool(info.get("is_installed") or (runner, app) in instalados)
            loja = _HEROIC_LOJAS[runner]
            descricao = f"Da sua conta {loja}, pelo Heroic."
            if info.get("isUbisoftManaged") or info.get("thirdPartyManagedApp") == "Uplay":
                descricao += " Abre o Ubisoft Connect junto."
            lista.append(
                Jogo(
                    id=f"heroic:{runner}:{app}",
                    nome=info.get("title") or app,
                    plataforma=loja,
                    tipo="pc",
                    colecao=loja,
                    descricao=descricao,
                    origem="heroic",
                    situacao=instalado,
                    acoes=["jogar", "desinstalar"] if instalado else ["instalar"],
                    capa_url=info.get("art_square") or info.get("art_cover") or "",
                    capa_alternativa=info.get("art_cover") or "",
                    saves=[info["save_path"]] if str(info.get("save_path", "")).startswith("/") else [],
                    extra={"runner": runner, "app": app, "pasta": pasta},
                )
            )
    return sorted(lista, key=lambda j: j.nome.lower())


def steam_no_portal() -> bool:
    """Jogos da Steam no portal? Por padrão não: a Steam abre pelo botão Guide do controle
    (ou pelo botão "Steam" do portal) e já tem a sua própria tela para escolher e jogar.
    Para mostrar, em ~/AllGames/config.toml: [steam] mostrar_no_portal = true."""
    return bool(configuracao().get("steam", {}).get("mostrar_no_portal", False))


def jogos() -> list[Jogo]:
    return (steam_jogos() if steam_no_portal() else []) + heroic_jogos()


# ------------------------------------------------------------------ ações


def _abrir(argv: list[str]) -> None:
    subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def _heroic_url(jogo: Jogo, gui: bool) -> str:
    consulta = urllib.parse.urlencode({"appName": jogo.extra["app"], "runner": jogo.extra["runner"]})
    return f"heroic://launch?{consulta}" + ("" if gui else "&gui=false")


def acao(jogo: Jogo, nome: str) -> str:
    """Instala ou desinstala pela loja. Devolve a mensagem para mostrar no portal."""
    if jogo.origem == "steam":
        steam = steam_comando()
        if not steam:
            raise RuntimeError("a Steam não está instalada no PC")
        _abrir([*steam, f"steam://{'install' if nome == 'instalar' else 'uninstall'}/{jogo.extra['appid']}"])
        return "Confirme na janela da Steam que abriu."
    if jogo.origem == "heroic":
        heroic = heroic_comando()
        if not heroic:
            raise RuntimeError("o Heroic não está instalado no PC")
        if nome == "instalar":
            # Abrir um jogo não instalado faz o Heroic perguntar se quer instalar.
            _abrir([*heroic, _heroic_url(jogo, gui=True)])
            return "O Heroic abriu: confirme a instalação na janela dele."
        _abrir(heroic)
        return f"O Heroic abriu: escolha {jogo.nome} e use Desinstalar."
    raise ValueError(f"{jogo.nome} não é de uma loja")


def abrir_big_picture() -> None:
    """Abre a Steam em tela cheia (Big Picture), a mesma tela do botão Guide do controle."""
    steam = steam_comando()
    if not steam:
        raise RuntimeError("a Steam não está instalada no PC")
    _abrir([*steam, "steam://open/bigpicture"])


def fechar_big_picture() -> None:
    """Fecha o Big Picture e volta para o que estava embaixo (o portal). Os jogos continuam abertos."""
    steam = steam_comando()
    if steam:
        _abrir([*steam, "steam://close/bigpicture"])


def abrir_downloads_steam() -> None:
    """Abre a tela de downloads da Steam (lá dá para pausar, retomar e mudar a ordem)."""
    steam = steam_comando()
    if not steam:
        raise RuntimeError("a Steam não está instalada no PC")
    _abrir([*steam, "steam://open/downloads"])


def jogar(jogo: Jogo) -> int:
    """Abre o jogo pela loja e espera até ele fechar (o Sunshine e o portal acompanham)."""
    if jogo.origem == "steam":
        steam = steam_comando()
        if not steam:
            raise RuntimeError("a Steam não está instalada no PC")
        appid = jogo.extra["appid"]
        _abrir([*steam, "-silent", f"steam://rungameid/{appid}"])
        # A Steam roda o jogo dentro do "reaper SteamLaunch AppId=<id>".
        apareceu = esperar_processo(lambda cmd, _: f"AppId={appid} " in cmd + " " and "SteamLaunch" in cmd)
        return 0 if apareceu else 1

    if jogo.origem == "heroic":
        heroic = heroic_comando()
        if not heroic:
            raise RuntimeError("o Heroic não está instalado no PC")
        pasta = jogo.extra.get("pasta", "").rstrip("/")
        _abrir([*heroic, _heroic_url(jogo, gui=False)])
        if not pasta:
            return 0
        nome_pasta = Path(pasta).name.lower()

        def achar(cmd: str, cwd: str) -> bool:
            # Jogos de Windows rodam no Wine com a pasta do jogo como pasta atual,
            # ou com o caminho dela (com \) na linha de comando.
            return cwd.startswith(pasta) or (nome_pasta and nome_pasta in cmd.lower().replace("\\", "/"))

        return 0 if esperar_processo(achar) else 1
    raise ValueError(f"{jogo.nome} não é de uma loja")
