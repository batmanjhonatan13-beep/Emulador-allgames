"""PortMaster: os ports de jogos do R36S, para pesquisar, instalar e jogar.

O PortMaster foi feito para portáteis ARM, mas parte dos ports também roda em
PC x86_64 (os mesmos que funcionam no Steam Deck). O AllGames lê o catálogo
oficial, mostra no portal só os que rodam aqui e usa o próprio instalador do
PortMaster (harbourmaster) para instalar e desinstalar.

O PortMaster fica em /opt/tools/PortMaster e os ports em /roms/ports, os
caminhos que ele mesmo procura (no Docker isso já vem pronto).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import caminhos
from .catalogo import Jogo

CATALOGO = "https://raw.githubusercontent.com/PortsMaster/PortMaster-Info/main/ports.json"
IMAGEM = "https://raw.githubusercontent.com/PortsMaster/PortMaster-New/main/ports/{pasta}/{arquivo}"
PACOTE = "https://github.com/PortsMaster/PortMaster-GUI/releases/latest/download/PortMaster.zip"


def pasta_ferramentas() -> Path:
    return Path(os.environ.get("ALLGAMES_PORTMASTER", "/opt/tools/PortMaster"))


def pasta_ports() -> Path:
    return Path(os.environ.get("ALLGAMES_PORTS", "/roms/ports"))


def instalado() -> bool:
    return (pasta_ferramentas() / "harbourmaster").exists()


def harbourmaster() -> list[str]:
    return [str(pasta_ferramentas() / "harbourmaster"), "--no-colour"]


def catalogo(baixar: bool = True) -> dict:
    """Catálogo oficial de ports, com cache de 6 horas (funciona sem internet com o último baixado)."""
    cache = caminhos.base() / ".cache-portmaster.json"
    try:
        dados = json.loads(cache.read_text())
        if not baixar or time.time() - cache.stat().st_mtime < 6 * 3600:
            return dados
    except (OSError, ValueError):
        dados = {}
    if not baixar:
        return dados
    try:
        with urllib.request.urlopen(CATALOGO, timeout=30) as resposta:
            novo = json.load(resposta)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(novo))
        return novo
    except (OSError, ValueError):
        return dados


def roda_aqui(port: dict) -> bool:
    """Ports que rodam em PC x86_64: os marcados para x86_64 ou para o Steam Deck."""
    atributos = port.get("attr", {})
    return "x86_64" in atributos.get("arch", []) or any(a.startswith("steamdeck") for a in atributos.get("avail", []))


def _imagem(nome_zip: str, port: dict) -> str:
    imagem = port.get("attr", {}).get("image", {}) or {}
    arquivo = imagem.get("screenshot")
    if not arquivo:
        return ""
    return IMAGEM.format(pasta=nome_zip.removesuffix(".zip"), arquivo=arquivo)


def jogos(dados: dict | None = None) -> list[Jogo]:
    if not instalado():
        return []
    ports = (dados if dados is not None else catalogo()).get("ports", {})
    lista = []
    for nome_zip, port in ports.items():
        if not roda_aqui(port):
            continue
        atributos = port.get("attr", {})
        itens = port.get("items") or []
        script = next((i for i in itens if i.endswith(".sh")), None)
        if not script:
            continue
        caminho_script = pasta_ports() / script
        esta_instalado = caminho_script.exists() and all((pasta_ports() / i).exists() for i in itens)
        pronto_para_jogar = bool(atributos.get("rtr"))
        instrucoes = (atributos.get("inst") or "").strip()
        descricao = (atributos.get("desc") or "").strip()
        pastas = [i for i in itens if not i.endswith(".sh")]
        lista.append(
            Jogo(
                id=f"port:{nome_zip}",
                nome=atributos.get("title") or nome_zip.removesuffix(".zip"),
                plataforma="PortMaster",
                tipo="port",
                colecao="PortMaster",
                descricao=descricao,
                controles=["controle"],
                saves=[f"{pasta_ports()}/{p}/{sub}/**/*" for p in pastas for sub in ("saves", "savedata", "conf")],
                origem="portmaster",
                situacao=esta_instalado,
                acoes=["jogar", "desinstalar"] if esta_instalado else ["instalar"],
                capa_url=_imagem(nome_zip, port),
                extra={
                    "nome_zip": nome_zip,
                    "script": str(caminho_script),
                    "combo_sair": True,
                    # Ports que não são "prontos para jogar" pedem os arquivos do jogo original.
                    "aviso": "" if pronto_para_jogar else instrucoes,
                    "generos": atributos.get("genres", []),
                },
            )
        )
    return sorted(lista, key=lambda j: j.nome.lower())


# Num PC, o PortMaster não reconhece um portátil e cai na plataforma "Unknown":
# sem um controle definido, ele joga a lista inteira de controles (~470 KB) numa
# variável de ambiente, o que estoura o limite do Linux e nenhum comando roda.
# Este arquivo (que o próprio PortMaster carrega) usa o controle virtual de
# Xbox 360 do Sunshine.
MOD_PC = """#!/bin/bash
# Gerado pelo AllGames: PC com Linux transmitindo pelo Sunshine (controle de Xbox 360).
if ! declare -f _allgames_get_controls >/dev/null; then
  eval "$(declare -f get_controls | sed '1s/get_controls/_allgames_get_controls/')"
  get_controls() { _allgames_get_controls "${1:-030000005e0400008e02000010010000}" "${2:-allgames}"; }
fi
"""


def nome_da_plataforma() -> str:
    """O nome que o PortMaster dá a um Linux comum: OS_NAME, NAME ou ID do os-release."""
    for arquivo in (Path("/etc/os-release"), Path("/usr/lib/os-release")):
        if not arquivo.exists():
            continue
        valores = {}
        for linha in arquivo.read_text(errors="replace").splitlines():
            chave, _, valor = linha.partition("=")
            valores[chave.strip()] = valor.strip().strip('"')
        for chave in ("OS_NAME", "NAME", "ID"):
            if valores.get(chave):
                return valores[chave]
    return "Unknown"


def _eh_x86_64(arquivo: Path) -> bool:
    try:
        cabecalho = arquivo.read_bytes()[:20]
    except OSError:
        return False
    # ELF com e_machine = 62 (x86-64)
    return cabecalho[:4] == b"\x7fELF" and int.from_bytes(cabecalho[18:20], "little") == 62


def _binarios_do_pc() -> None:
    """Põe as versões x86_64 das ferramentas (gptokeyb...) no lugar das de ARM.

    O PortMaster vem com as duas; num portátil ARM ele usa a sem sufixo, então
    num PC a sem sufixo precisa ser a cópia da .x86_64.
    """
    for versao_pc in pasta_ferramentas().glob("*.x86_64"):
        destino = versao_pc.with_suffix("")
        if not _eh_x86_64(destino) and _eh_x86_64(versao_pc):
            shutil.copy2(versao_pc, destino)
            destino.chmod(0o755)


def preparar_ambiente() -> None:
    try:
        _binarios_do_pc()
    except OSError:
        pass
    for nome in dict.fromkeys(["Unknown", nome_da_plataforma()]):
        destino = pasta_ferramentas() / f"mod_{nome}.txt"
        try:
            if not destino.exists() or destino.read_text() != MOD_PC:
                destino.write_text(MOD_PC)
        except OSError:
            pass  # sem permissão na pasta do PortMaster: o port ainda tenta rodar


def comando(jogo: Jogo) -> list[str]:
    preparar_ambiente()
    return ["bash", jogo.extra["script"]]


def comando_instalar(jogo: Jogo) -> list[str]:
    return [sys.executable, str(caminhos.EXECUTAVEL), "portmaster", "instalar", jogo.extra["nome_zip"]]


def comando_desinstalar(jogo: Jogo) -> list[str]:
    return [sys.executable, str(caminhos.EXECUTAVEL), "portmaster", "desinstalar", jogo.extra["nome_zip"]]


def instalar(nome_zip: str) -> None:
    """Baixa o port, confere o MD5 do catálogo e instala pelo harbourmaster."""
    if not instalado():
        raise RuntimeError(
            f"o PortMaster não está instalado em {pasta_ferramentas()} (rode scripts/instalar-portmaster.sh)"
        )
    port = catalogo().get("ports", {}).get(nome_zip)
    if not port:
        raise ValueError(f"{nome_zip} não está no catálogo do PortMaster")
    fonte = port.get("source", {})
    pasta = caminhos.base() / ".cache-ports"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / nome_zip
    print(f"Baixando {fonte['url']}")
    with urllib.request.urlopen(fonte["url"], timeout=600) as resposta:
        arquivo.write_bytes(resposta.read())
    try:
        if fonte.get("md5") and hashlib.md5(arquivo.read_bytes()).hexdigest() != fonte["md5"]:
            raise RuntimeError(f"o arquivo baixado de {nome_zip} veio corrompido (MD5 diferente)")
        argv = [*harbourmaster(), "install", str(arquivo)]
        # Sem runtimes extras (Godot, Java...) não precisa consultar a internet.
        if not port.get("attr", {}).get("runtime"):
            argv.append("--offline")
        _rodar_harbourmaster(argv)
    finally:
        arquivo.unlink(missing_ok=True)


def desinstalar(nome_zip: str) -> None:
    _rodar_harbourmaster([*harbourmaster(), "--offline", "uninstall", nome_zip])


def _rodar_harbourmaster(argv: list[str]) -> None:
    # O harbourmaster escolhe as pastas olhando a pasta atual (numa pasta com .git ele
    # entra em "modo de desenvolvimento"), então ele sempre roda de dentro da pasta dele.
    subprocess.run(argv, check=True, cwd=pasta_ferramentas())
