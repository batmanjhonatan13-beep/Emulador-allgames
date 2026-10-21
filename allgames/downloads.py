"""Downloads de jogos e espaço em disco, para acompanhar pelo celular.

- Steam: o progresso vem dos arquivos que a própria Steam atualiza enquanto
  baixa (appmanifest_*.acf). Pausar e retomar é feito na tela de downloads da
  Steam, que o portal abre.
- Epic: o AllGames baixa pelo legendary (o mesmo motor que o Heroic usa, com a
  mesma conta), então dá para ver o progresso, pausar, continuar e parar.
"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from . import caminhos, lojas, sistemas

# Bits de StateFlags da Steam (EAppState)
_STEAM_PAUSADO = 512
_STEAM_ATIVO = 256 | 1024 | 524288 | 1048576 | 2097152 | 4194304

_UNIDADES = {"b": 1, "kib": 1024, "mib": 1024**2, "gib": 1024**3, "tib": 1024**4}
_PROGRESSO = re.compile(r"Progress: ([\d.]+)%.*ETA: (\d+):(\d+):(\d+)")
_BAIXADO = re.compile(r"Downloaded: ([\d.]+) (\w+)")
_VELOCIDADE = re.compile(r"\+ Download\s*-\s*([\d.]+) (\w+)/s")
_TAMANHO = re.compile(r"Download size: ([\d.]+) (\w+)")
_PASTA = re.compile(r"Install path: (.+)")


def _bytes(valor: str, unidade: str) -> int:
    return int(float(valor) * _UNIDADES.get(unidade.lower(), 1))


# ------------------------------------------------------------------ disco


def pasta_epic() -> Path:
    """Onde os jogos da Epic são instalados: config.toml, /mnt/games (Docker) ou ~/Games/Heroic."""
    configurada = lojas.configuracao().get("epic", {}).get("pasta")
    if configurada:
        return Path(configurada).expanduser()
    if Path("/mnt/games").is_dir():
        return Path("/mnt/games/Epic")
    return Path.home() / "Games/Heroic"


def discos() -> list[dict]:
    """Espaço livre em cada disco usado pelos jogos (um item por disco físico)."""
    lugares = [(b.parent, "Steam") for b in lojas.steam_bibliotecas()]
    lugares += [(pasta_epic(), "Epic"), (sistemas.roms_dir(), "ROMs"), (caminhos.base(), "AllGames")]
    por_disco: dict[int, dict] = {}
    for caminho, nome in lugares:
        existente = caminho
        while not existente.exists() and existente != existente.parent:
            existente = existente.parent
        try:
            dispositivo = existente.stat().st_dev
            uso = shutil.disk_usage(existente)
        except OSError:
            continue
        disco = por_disco.setdefault(
            dispositivo, {"nomes": [], "caminho": str(existente), "livre": uso.free, "total": uso.total}
        )
        if nome not in disco["nomes"]:
            disco["nomes"].append(nome)
    return list(por_disco.values())


def livre_em(caminho: Path) -> int:
    while not caminho.exists() and caminho != caminho.parent:
        caminho = caminho.parent
    return shutil.disk_usage(caminho).free


# ------------------------------------------------------------------ Steam


def steam_downloads() -> list[dict]:
    lista = []
    for biblioteca, app in lojas.steam_manifestos():
        flags = int(app.get("StateFlags", 0))
        total = int(app.get("BytesToDownload", 0) or 0)
        feito = int(app.get("BytesDownloaded", 0) or 0)
        if not (flags & (_STEAM_ATIVO | _STEAM_PAUSADO) or (total and feito < total)):
            continue
        if flags & _STEAM_PAUSADO:
            estado = "pausado"
        elif flags & _STEAM_ATIVO:
            estado = "baixando"
        else:
            estado = "na fila"
        lista.append(
            {
                "id": f"steam:{app['appid']}",
                "nome": app["name"],
                "loja": "Steam",
                "estado": estado,
                "baixado": feito,
                "total": total,
                "pasta": str(biblioteca.parent),
                "acoes": ["abrir_steam"],
            }
        )
    return lista


# ------------------------------------------------------------------ Epic (legendary)


def legendary() -> list[str] | None:
    binario = shutil.which("legendary")
    return [binario] if binario else None


def _ambiente_legendary() -> dict[str, str]:
    env = dict(os.environ)
    raiz = lojas.heroic_raiz()
    if raiz and (raiz / "legendaryConfig/legendary").is_dir():
        # A mesma conta e a mesma lista de instalados do Heroic.
        env["LEGENDARY_CONFIG_PATH"] = str(raiz / "legendaryConfig/legendary")
    return env


def epic_tamanho(app: str) -> tuple[int, int] | None:
    """(download, instalado) em bytes, pela Epic; None se não der para saber."""
    comando = legendary()
    if not comando:
        return None
    try:
        saida = subprocess.run(
            [*comando, "info", app, "--json"], capture_output=True, text=True, timeout=60, env=_ambiente_legendary()
        )
        manifesto = json.loads(saida.stdout).get("manifest") or {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    if not manifesto.get("download_size"):
        return None
    return int(manifesto["download_size"]), int(manifesto.get("disk_size") or manifesto["download_size"])


class DownloadEpic:
    def __init__(self, id_: str, app: str, nome: str, estado: str = "na fila", baixado: int = 0, total: int = 0):
        self.id, self.app, self.nome = id_, app, nome
        self.estado, self.baixado, self.total = estado, baixado, total
        self.velocidade = 0
        self.restante = None  # segundos
        self.pasta = ""
        self.erro = ""
        self._antes = 0
        self._processo: subprocess.Popen | None = None
        self._parando = False

    def iniciar(self, ao_mudar) -> None:
        comando = legendary()
        if not comando:
            raise RuntimeError("o legendary não está instalado (veja docs/LOJAS.md)")
        base = pasta_epic()
        base.mkdir(parents=True, exist_ok=True)
        caminhos.logs().mkdir(parents=True, exist_ok=True)
        self.estado, self.erro, self._parando = "baixando", "", False
        self._processo = subprocess.Popen(
            [*comando, "install", self.app, "-y", "--base-path", str(base)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=_ambiente_legendary(),
        )
        threading.Thread(target=self._acompanhar, args=(ao_mudar,), daemon=True).start()

    def _acompanhar(self, ao_mudar) -> None:
        with (caminhos.logs() / "downloads.log").open("a") as log, self._processo.stdout:
            for linha in self._processo.stdout:
                log.write(linha)
                self._ler(linha)
        codigo = self._processo.wait()
        if self._parando:
            self.estado = "pausado"
        elif codigo == 0:
            self.estado, self.baixado = "concluido", max(self.baixado, self.total)
        else:
            self.estado, self.erro = "erro", "o download falhou; veja ~/AllGames/logs/downloads.log"
        self.velocidade, self.restante = 0, None
        ao_mudar()

    def _ler(self, linha: str) -> None:
        # Ao continuar, o legendary só conta o que falta baixar: o que já veio antes
        # fica em self._antes para a barra não voltar para trás.
        if m := _TAMANHO.search(linha):
            falta = _bytes(*m.groups())
            self._antes = self.total - falta if 0 < falta < self.total else 0
            self.total = self._antes + falta
        if m := _PASTA.search(linha):
            self.pasta = m.group(1).strip()
        if m := _BAIXADO.search(linha):
            self.baixado = self._antes + _bytes(*m.groups())
        if m := _VELOCIDADE.search(linha):
            self.velocidade = _bytes(*m.groups())
        if m := _PROGRESSO.search(linha):
            h, mi, se = (int(x) for x in m.groups()[1:])
            self.restante = h * 3600 + mi * 60 + se
            if self.total:
                feito = (self.total - self._antes) * float(m.group(1)) / 100
                self.baixado = max(self.baixado, int(self._antes + feito))

    def pausar(self) -> None:
        if self._processo and self._processo.poll() is None:
            self._parando = True
            self._processo.terminate()  # o legendary continua de onde parou na próxima vez

    def como_dict(self) -> dict:
        acoes = {"baixando": ["pausar"], "pausado": ["continuar", "cancelar"], "erro": ["continuar", "cancelar"]}
        return {
            "id": self.id,
            "nome": self.nome,
            "loja": "Epic Games",
            "estado": self.estado,
            "baixado": self.baixado,
            "total": self.total,
            "velocidade": self.velocidade,
            "restante": self.restante,
            "pasta": self.pasta or str(pasta_epic()),
            "erro": self.erro,
            "acoes": acoes.get(self.estado, []),
        }


class Downloads:
    """Fila de downloads da Epic (guardada em disco para sobreviver a reinícios) + Steam."""

    def __init__(self, arquivo: Path | None = None):
        self.arquivo = arquivo or caminhos.base() / "downloads.json"
        self._trava = threading.Lock()
        self.epic: dict[str, DownloadEpic] = {}
        self._amostras: dict[str, tuple[float, int]] = {}
        try:
            for item in json.loads(self.arquivo.read_text()):
                estado = "pausado" if item["estado"] in ("baixando", "na fila") else item["estado"]
                self.epic[item["id"]] = DownloadEpic(
                    item["id"], item["app"], item["nome"], estado, item.get("baixado", 0), item.get("total", 0)
                )
        except (OSError, ValueError, KeyError):
            pass

    def _salvar(self) -> None:
        # Chamado também pelas threads dos downloads: grava inteiro ou nada.
        with self._trava:
            dados = [
                {"id": d.id, "app": d.app, "nome": d.nome, "estado": d.estado, "baixado": d.baixado, "total": d.total}
                for d in self.epic.values()
                if d.estado != "concluido"
            ]
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            temporario = self.arquivo.with_suffix(".tmp")
            temporario.write_text(json.dumps(dados))
            temporario.replace(self.arquivo)

    def baixar_epic(self, id_: str, app: str, nome: str) -> DownloadEpic:
        with self._trava:
            download = self.epic.get(id_) or DownloadEpic(id_, app, nome)
            self.epic[id_] = download
        if download.estado != "baixando":
            download.iniciar(self._salvar)
        self._salvar()
        return download

    def acao(self, id_: str, nome: str) -> None:
        download = self.epic.get(id_)
        if not download:
            raise ValueError("download não encontrado")
        if nome == "pausar":
            download.pausar()
        elif nome == "continuar":
            if download.estado != "baixando":
                download.iniciar(self._salvar)
        elif nome == "cancelar":
            download.pausar()
            with self._trava:
                self.epic.pop(id_, None)
        else:
            raise ValueError(f"ação desconhecida: {nome}")
        self._salvar()

    def lista(self) -> list[dict]:
        with self._trava:
            epic = list(self.epic.values())
        itens = steam_downloads() + [d.como_dict() for d in epic]
        agora = time.monotonic()
        for item in itens:
            # Velocidade e tempo restante da Steam a partir de leituras seguidas.
            if item["loja"] == "Steam":
                anterior = self._amostras.get(item["id"])
                self._amostras[item["id"]] = (agora, item["baixado"])
                velocidade = 0
                if anterior and agora > anterior[0] and item["estado"] == "baixando":
                    velocidade = max(0, int((item["baixado"] - anterior[1]) / (agora - anterior[0])))
                item["velocidade"] = velocidade
                faltam = item["total"] - item["baixado"]
                item["restante"] = int(faltam / velocidade) if velocidade else None
            item["livre"] = livre_em(Path(item["pasta"])) if item.get("pasta") else None
            item["cabe"] = item["livre"] is None or item["total"] - item["baixado"] <= item["livre"]
        return itens
