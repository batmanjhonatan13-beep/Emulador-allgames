"""`allgames doutor`: confere se o PC está pronto para transmitir jogos ao celular."""

import grp
import os
import pwd
import shutil
import subprocess
import sys
from pathlib import Path

from . import caminhos, downloads, portal, portmaster, sunshine


def _rodar(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _sistema() -> tuple[bool, str, str]:
    info = {}
    if Path("/etc/os-release").exists():
        for linha in Path("/etc/os-release").read_text().splitlines():
            chave, _, valor = linha.partition("=")
            info[chave] = valor.strip('"')
    nome = info.get("PRETTY_NAME", "desconhecido")
    sessao = os.environ.get("XDG_SESSION_TYPE", "?")
    return True, f"{nome} (sessão {sessao})", ""


def _python() -> tuple[bool, str, str]:
    ok = sys.version_info >= (3, 10)
    return ok, f"Python {sys.version.split()[0]}", "" if ok else "precisa do Python 3.10 ou mais novo"


SUNSHINE_DOCKER = Path("/usr/local/libexec/steam-headless/sunshine")


def _sunshine_instalado() -> tuple[bool, str, str]:
    if caminhos.no_docker():
        if SUNSHINE_DOCKER.exists():
            return True, "Sunshine da imagem Docker (captura pela tela virtual do KWin)", ""
        return False, "Sunshine não encontrado na imagem", "reconstrua a imagem: docker compose build --pull"
    binario = shutil.which("sunshine")
    if not binario:
        return False, "Sunshine não encontrado", "rode scripts/instalar-host.sh"
    real = os.path.realpath(binario)
    caps = _rodar("getcap", real)
    if "cap_sys_admin" not in caps:
        return False, f"Sunshine em {real} sem captura KMS", f"sudo setcap cap_sys_admin+p {real}"
    return True, f"Sunshine em {real} (captura KMS liberada)", ""


def _sunshine_rodando() -> tuple[bool, str, str]:
    nome = sunshine.servico_ativo()
    if nome:
        return True, f"serviço {nome} ativo — painel em https://localhost:47990", ""
    if caminhos.no_docker():
        return False, "Sunshine parado", "termine a configuração em http://IP-DO-PC:8483 (ele só liga depois disso)"
    return False, "serviço do Sunshine parado", "systemctl --user enable --now app-dev.lizardbyte.app.Sunshine"


def _codificador() -> tuple[bool, str, str]:
    if shutil.which("nvidia-smi"):
        gpu = _rodar("nvidia-smi", "--query-gpu=name", "--format=csv,noheader").splitlines()
        return True, f"NVIDIA {gpu[0] if gpu else ''} → NVENC", ""
    if caminhos.no_docker():
        # Na imagem o próprio Sunshine escolhe VA-API pela GPU que recebeu.
        placas = sorted(str(p) for p in Path("/dev/dri").glob("renderD*"))
        if placas:
            return True, f"GPU {placas[0]} → VA-API", ""
        return False, "o container não recebeu a GPU", "confira GPU= no docker/.env (ex.: /dev/dri/renderD128)"
    if shutil.which("vainfo"):
        saida = _rodar("vainfo")
        if "VAEntrypointEncSlice" in saida or "VAEntrypointEncSliceLP" in saida:
            return True, "VA-API com codificação por hardware (AMD/Intel)", ""
        return (
            False,
            "VA-API sem codificação por hardware",
            "sudo apt install mesa-va-drivers (AMD) ou intel-media-va-driver-non-free (Intel)",
        )
    return False, "não achei nvidia-smi nem vainfo", "sudo apt install vainfo  # para testar AMD/Intel"


def _entrada() -> tuple[bool, str, str]:
    if os.access("/dev/uinput", os.W_OK):
        return True, "/dev/uinput liberado (controle virtual funciona)", ""
    if caminhos.no_docker():
        return False, "sem acesso a /dev/uinput", "o docker-compose precisa passar /dev/uinput (veja docs/DOCKER.md)"
    usuario = pwd.getpwuid(os.getuid()).pw_name
    try:
        no_grupo = usuario in grp.getgrnam("input").gr_mem
    except KeyError:
        no_grupo = False
    dica = (
        "faça logout/login para valer o grupo input" if no_grupo else "sudo usermod -aG input $USER e faça logout/login"
    )
    return False, "sem acesso a /dev/uinput (controle e toque não funcionam)", dica


def _tailscale() -> tuple[bool, str, str]:
    if caminhos.no_docker():
        # O Tailscale fica no PC; com a rede "host" o container enxerga a interface dele.
        if Path("/sys/class/net/tailscale0").exists():
            return True, "Tailscale do PC ativo (dá para jogar fora de casa)", ""
        return False, "Tailscale não está no PC (só joga na mesma rede Wi-Fi)", "no PC: scripts/instalar-tailscale.sh"
    if not shutil.which("tailscale"):
        return False, "Tailscale não instalado (só joga na mesma rede Wi-Fi)", "rode scripts/instalar-tailscale.sh"
    ip = _rodar("tailscale", "ip", "-4")
    if not ip:
        return False, "Tailscale instalado mas desconectado", "sudo tailscale up"
    return True, f"Tailscale conectado — use {ip.splitlines()[0]} no Moonlight fora de casa", ""


def _portal() -> tuple[bool, str, str]:
    for nome in portal.NAVEGADORES:
        if shutil.which(nome):
            return True, f"tela de capas abre no {nome} (app AllGames no Moonlight)", ""
    return False, "nenhum navegador para a tela de capas", "sudo apt install firefox"


def _pastas() -> tuple[bool, str, str]:
    pasta = caminhos.originais()
    if not pasta.is_dir():
        return False, f"pasta de originais não existe: {pasta}", f"mkdir -p {pasta}"
    return True, f"originais em {pasta} ({sum(1 for _ in pasta.iterdir())} arquivos)", ""


def _portmaster() -> tuple[bool, str, str]:
    if not portmaster.instalado():
        return False, "PortMaster não instalado", "rode scripts/instalar-portmaster.sh (no Docker já vem pronto)"
    ports = sum(1 for _ in portmaster.pasta_ports().glob("*.sh")) if portmaster.pasta_ports().is_dir() else 0
    return True, f"PortMaster em {portmaster.pasta_ferramentas()} ({ports} ports instalados)", ""


def _epic() -> tuple[bool, str, str]:
    if not downloads.legendary():
        return (
            False,
            "sem legendary: a Epic baixa só pelo Heroic",
            "pipx install legendary-gl (no Docker já vem pronto)",
        )
    return True, f"downloads da Epic pelo portal (jogos em {downloads.pasta_epic()})", ""


VERIFICACOES = [
    ("Sistema", _sistema),
    ("Python", _python),
    ("Sunshine", _sunshine_instalado),
    ("Serviço", _sunshine_rodando),
    ("Vídeo", _codificador),
    ("Controles", _entrada),
    ("Acesso remoto", _tailscale),
    ("Portal", _portal),
    ("PortMaster", _portmaster),
    ("Epic", _epic),
    ("Jogos", _pastas),
]


def executar() -> int:
    problemas = 0
    for titulo, verificacao in VERIFICACOES:
        ok, texto, dica = verificacao()
        print(f"{'✔' if ok else '✘'} {titulo:<14} {texto}")
        if dica:
            print(f"  {'':<14} → {dica}")
        problemas += not ok
    print()
    print("Tudo pronto!" if not problemas else f"{problemas} item(ns) para resolver.")
    return 1 if problemas else 0
