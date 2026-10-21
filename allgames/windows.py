"""AllGames no Windows: onde ficam os programas e como baixar os emuladores.

No Windows não há Docker nem Flatpak. O instalador (scripts/instalar-windows.ps1)
põe o Sunshine, o RetroArch e o Python pelo winget; o AllGames baixa os cores do
RetroArch e os outros emuladores (zip das páginas oficiais) para ~/AllGames/emuladores.
Lá o celular mostra a própria tela do PC (o Sunshine do Windows), e a Steam é a do PC.
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ATIVO = sys.platform == "win32"
SERVICO_SUNSHINE = "SunshineService"


def _pasta(variavel: str, padrao: str) -> Path:
    return Path(os.environ.get(variavel) or padrao)


def appdata() -> Path:
    return _pasta("APPDATA", str(Path.home() / "AppData/Roaming"))


def _primeiro(candidatos) -> Path | None:
    return next((Path(c) for c in candidatos if c and Path(c).is_file()), None)


def retroarch() -> Path | None:
    """O RetroArch do winget (C:\\RetroArch-Win64) ou outro que você tenha."""
    return _primeiro(
        [
            os.environ.get("ALLGAMES_RETROARCH"),
            Path("C:/RetroArch-Win64/retroarch.exe"),
            _pasta("LOCALAPPDATA", "") / "Programs/RetroArch/retroarch.exe",
            _pasta("ProgramFiles", "C:/Program Files") / "RetroArch/retroarch.exe",
            shutil.which("retroarch"),
        ]
    )


def edge() -> Path | None:
    """O Edge vem com o Windows: o portal abre nele em tela cheia."""
    return _primeiro(
        [
            _pasta("ProgramFiles(x86)", "C:/Program Files (x86)") / "Microsoft/Edge/Application/msedge.exe",
            _pasta("ProgramFiles", "C:/Program Files") / "Microsoft/Edge/Application/msedge.exe",
            shutil.which("msedge"),
        ]
    )


def steam() -> Path | None:
    caminho = None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as chave:
            caminho = winreg.QueryValueEx(chave, "SteamExe")[0]
    except (ImportError, OSError):
        pass
    return _primeiro([caminho, _pasta("ProgramFiles(x86)", "C:/Program Files (x86)") / "Steam/steam.exe"])


def sunshine_config() -> Path:
    return _pasta("ProgramFiles", "C:/Program Files") / "Sunshine/config"


def sunshine_ativo() -> bool:
    r = subprocess.run(["sc", "query", SERVICO_SUNSHINE], capture_output=True, text=True)
    return "RUNNING" in r.stdout


def reiniciar_sunshine() -> bool:
    """Precisa de administrador (o instalador roda assim)."""
    comando = f"Restart-Service -Name {SERVICO_SUNSHINE}"
    return subprocess.run(["powershell", "-NoProfile", "-Command", comando], capture_output=True).returncode == 0


def exe_baixado(pasta: Path, exe: str) -> Path | None:
    """O executável dentro do zip extraído (alguns zips têm uma pasta dentro)."""
    if not pasta.is_dir():
        return None
    return next((p for p in sorted(pasta.rglob("*")) if p.name.lower() == exe.lower() and p.is_file()), None)


def _baixar(url: str, timeout: int = 600) -> bytes:
    pedido = urllib.request.Request(url, headers={"User-Agent": "AllGames"})
    with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
        return resposta.read()


def escolher_arquivo(assets: list[dict], padroes: list[str]) -> dict | None:
    for padrao in padroes:
        achado = next((a for a in assets if re.search(padrao, a.get("name", ""))), None)
        if achado:
            return achado
    return None


def baixar_zip(releases: list[str], padroes: list[str], pasta: Path) -> Path:
    """Baixa a última versão de um emulador (página de releases, como no GitHub) e extrai em `pasta`."""
    erros = []
    for api in releases:
        try:
            assets = json.loads(_baixar(api, 30)).get("assets", [])
        except (OSError, ValueError) as erro:
            erros.append(f"{api}: {erro}")
            continue
        escolhido = escolher_arquivo(assets, padroes)
        if not escolhido:
            erros.append(f"{api}: nenhum zip para Windows na última versão")
            continue
        print(f"  baixando {escolhido['name']}")
        dados = _baixar(escolhido["browser_download_url"])
        temporaria = pasta.with_name(f".{pasta.name}.novo")
        shutil.rmtree(temporaria, ignore_errors=True)
        with zipfile.ZipFile(io.BytesIO(dados)) as pacote:
            pacote.extractall(temporaria)
        shutil.rmtree(pasta, ignore_errors=True)
        temporaria.replace(pasta)
        return pasta
    raise RuntimeError("não consegui baixar: " + "; ".join(erros))
