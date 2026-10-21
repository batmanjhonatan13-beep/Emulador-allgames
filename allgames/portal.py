"""Portal: a tela com as capas dos jogos, no estilo do Game Pass.

O portal é uma página web servida pelo próprio PC. No modo `--kiosk` ele abre um
navegador em tela cheia e vira um app do Sunshine ("AllGames"): você abre no
Moonlight, escolhe o jogo pela capa (tocando ou com o controle) e o jogo abre no
PC. Ao fechar o jogo, você volta para o portal.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import caminhos, capas, downloads, lojas, portmaster, saves, sistemas, supervisor, windows
from .catalogo import Jogo, verificar

# Cada sessão do AllGames no mesmo PC (Docker com rede do host) usa uma porta: ALLGAMES_PORTA.
PORTA = int(os.environ.get("ALLGAMES_PORTA") or 47800)
ARQUIVOS = {"/": "index.html", "/estilo.css": "estilo.css", "/app.js": "app.js"}
TIPOS_DE_ARQUIVO = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript"}
NAVEGADORES = ["chromium", "chromium-browser", "google-chrome", "brave-browser", "firefox"]
NOMES_DOS_TIPOS = {"port": "Port nativo", "recomp": "Recompilação", "emulador": "Emulador", "pc": "Jogo de PC"}


def _data(timestamp: float | None) -> str | None:
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds") if timestamp else None


def _capa(jogo: Jogo) -> str | None:
    if jogo.capa_url:
        return jogo.capa_url
    if jogo.capa or capas.obter(jogo, baixar=False):
        return "/capa?" + urllib.parse.urlencode({"id": jogo.id})
    return None


def acoes(jogo: Jogo) -> list[str]:
    """O que o portal pode fazer com o jogo."""
    if jogo.origem != "catalogo":
        return jogo.acoes
    if jogo.instalado:
        return ["jogar"]
    # Jogos do catálogo só instalam com os arquivos originais no PC.
    return [] if any(not v.ok for v in verificar(jogo)) else ["instalar"]


def descrever(
    jogo: Jogo, tarefa: str | None = None, download: dict | None = None, pastas: saves.Pastas | None = None
) -> dict:
    return {
        "id": jogo.id,
        "nome": jogo.nome,
        "plataforma": jogo.plataforma,
        "tipo": NOMES_DOS_TIPOS[jogo.tipo],
        "colecao": jogo.colecao,
        "descricao": jogo.descricao,
        "controles": jogo.controles,
        "instalado": jogo.instalado,
        "falta": [v.problema for v in verificar(jogo) if not v.ok],
        "capa": _capa(jogo),
        "capa_alternativa": jogo.capa_alternativa or None,
        "origem": jogo.origem,
        "acoes": acoes(jogo),
        "pendente": jogo.extra.get("falta", ""),
        "aviso": jogo.extra.get("aviso", ""),
        "tarefa": tarefa,
        "download": (
            {"estado": download["estado"], "progresso": round(100 * download["baixado"] / download["total"])}
            if download and download["total"]
            else None
        ),
        "ultimo_save": _data(saves.ultimo_save(jogo, pastas)),
        "jogado_em": _data(jogo.jogado_em),
    }


def versao_da_biblioteca() -> str:
    """Muda quando entra ou sai um jogo das pastas: o portal confere de tempos em tempos e só
    recarrega a lista (que lê milhares de ROMs) quando ela mudou."""
    partes = []
    for raiz in (sistemas.roms_dir(), portmaster.pasta_ports()):
        if not raiz.is_dir():
            continue
        # As ROMs ficam até 2 níveis dentro da pasta do console: basta olhar as pastas.
        pastas = [raiz]
        for pasta in raiz.iterdir():
            if pasta.is_dir():
                pastas.append(pasta)
                pastas += [sub for sub in pasta.iterdir() if sub.is_dir()]
        for pasta in pastas:
            try:
                partes.append(f"{pasta}:{pasta.stat().st_mtime_ns}")
            except OSError:
                continue
    return hashlib.sha1("|".join(partes).encode()).hexdigest()[:16]


class Partida:
    """O jogo aberto pelo portal (um por vez)."""

    def __init__(self, comando):
        self._comando = comando
        self._processo: subprocess.Popen | None = None
        self._jogo: str | None = None
        self._trava = threading.Lock()

    @property
    def jogo(self) -> str | None:
        with self._trava:
            if self._processo and self._processo.poll() is not None:
                self._processo = self._jogo = None
            return self._jogo

    def iniciar(self, jogo: Jogo) -> bool:
        if self.jogo:
            return False
        with self._trava:
            self._processo = subprocess.Popen(self._comando(jogo))
            self._jogo = jogo.id
        return True

    def encerrar(self) -> None:
        with self._trava:
            if self._processo and self._processo.poll() is None:
                self._processo.terminate()
                try:
                    self._processo.wait(10)
                except subprocess.TimeoutExpired:
                    self._processo.kill()


class Tarefas:
    """Instalações em segundo plano (emuladores, jogos do catálogo)."""

    def __init__(self):
        self._processos: dict[str, subprocess.Popen] = {}
        self._trava = threading.Lock()

    def situacao(self, id_: str) -> str | None:
        with self._trava:
            processo = self._processos.get(id_)
            if not processo:
                return None
            if processo.poll() is None:
                return "instalando"
            return "erro" if processo.returncode else None

    def iniciar(self, id_: str, argv: list[str]) -> bool:
        if self.situacao(id_) == "instalando":
            return False
        caminhos.logs().mkdir(parents=True, exist_ok=True)
        log = open(caminhos.logs() / "instalacoes.log", "ab")  # noqa: SIM115 - fica aberto com o processo
        with self._trava:
            self._processos[id_] = subprocess.Popen(argv, stdout=log, stderr=log, stdin=subprocess.DEVNULL)
        return True


class Portal(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, endereco, carregar_jogos, comando, ao_sair=None):
        super().__init__(endereco, Handler)
        self.carregar_jogos = carregar_jogos
        self.jogos: dict[str, Jogo] = {}
        self.partida = Partida(comando)
        self.tarefas = Tarefas()
        self.downloads = downloads.Downloads()
        self.ao_sair = ao_sair

    def atualizar(self) -> dict[str, Jogo]:
        self.jogos = {j.id: j for j in self.carregar_jogos()}
        return self.jogos

    def jogo(self, id_: str | None) -> Jogo | None:
        if not id_:
            return None
        return self.jogos.get(id_) or self.atualizar().get(id_)


class Handler(BaseHTTPRequestHandler):
    server: Portal

    def log_message(self, formato, *args):
        pass

    def _responder(self, status: int, corpo: bytes = b"", tipo: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, dados, status: int = HTTPStatus.OK) -> None:
        self._responder(status, json.dumps(dados, ensure_ascii=False).encode())

    def _id(self) -> str | None:
        return urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("id", [None])[0]

    def do_GET(self):
        caminho = urllib.parse.urlparse(self.path).path
        if caminho in ARQUIVOS:
            arquivo = caminhos.PORTAL / ARQUIVOS[caminho]
            self._responder(HTTPStatus.OK, arquivo.read_bytes(), TIPOS_DE_ARQUIVO[arquivo.suffix])
        elif caminho == "/api/jogos":
            tarefas = self.server.tarefas
            baixando = {d["id"]: d for d in self.server.downloads.lista()}
            pastas = saves.Pastas()  # cada pasta de ROMs é lida uma vez, não uma vez por ROM
            jogos = [
                descrever(j, tarefas.situacao(j.id), baixando.get(j.id), pastas)
                for j in self.server.atualizar().values()
            ]
            self._json(
                {
                    "jogos": jogos,
                    "jogando": self.server.partida.jogo,
                    "pode_sair": bool(self.server.ao_sair),
                    "downloads_ativos": sum(d["estado"] == "baixando" for d in baixando.values()),
                    "versao": versao_da_biblioteca(),
                }
            )
        elif caminho == "/api/downloads":
            self._json({"downloads": self.server.downloads.lista(), "discos": downloads.discos()})
        elif caminho == "/api/versao":
            self._json({"versao": versao_da_biblioteca()})
        elif caminho == "/api/estado":
            self._json({"jogando": self.server.partida.jogo})
        elif caminho == "/capa":
            jogo = self.server.jogo(self._id())
            capa = capas.obter(jogo) if jogo else None
            if capa:
                tipo = "image/jpeg" if capa.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                self._responder(HTTPStatus.OK, capa.read_bytes(), tipo)
            else:
                self._responder(HTTPStatus.NOT_FOUND)
        else:
            self._responder(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        # Um site qualquer aberto no navegador não consegue mandar este cabeçalho
        # para cá (bloqueado pelo CORS), então só a própria página abre jogos.
        if self.headers.get("X-AllGames") != "1":
            return self._responder(HTTPStatus.FORBIDDEN)
        caminho = urllib.parse.urlparse(self.path).path
        if caminho in ("/api/jogar", "/api/instalar", "/api/desinstalar"):
            jogo = self.server.jogo(self._id())
            if not jogo:
                return self._json({"erro": "jogo desconhecido"}, HTTPStatus.NOT_FOUND)
            acao = caminho.removeprefix("/api/")
            if acao not in acoes(jogo):
                return self._json({"erro": f"não dá para {acao} {jogo.nome} por aqui"}, HTTPStatus.CONFLICT)
            try:
                return getattr(self, f"_{acao}")(jogo)
            except (RuntimeError, ValueError) as erro:
                return self._json({"erro": str(erro)}, HTTPStatus.CONFLICT)
        if caminho == "/api/download":
            consulta = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            acao = consulta.get("acao", [""])[0]
            try:
                if acao == "abrir_steam":
                    lojas.abrir_downloads_steam()
                else:
                    self.server.downloads.acao(self._id() or "", acao)
            except (RuntimeError, ValueError) as erro:
                return self._json({"erro": str(erro)}, HTTPStatus.CONFLICT)
            return self._json({"ok": True})
        if caminho == "/api/steam":
            try:
                lojas.abrir_big_picture()
            except RuntimeError as erro:
                return self._json({"erro": str(erro)}, HTTPStatus.CONFLICT)
            return self._json({"ok": True})
        if caminho == "/api/encerrar":
            self.server.partida.encerrar()
            return self._json({"jogando": None})
        if caminho == "/api/sair" and self.server.ao_sair:
            self._json({"saindo": True})
            self.server.partida.encerrar()
            threading.Thread(target=self.server.ao_sair, daemon=True).start()
            return None
        return self._responder(HTTPStatus.NOT_FOUND)

    def _jogar(self, jogo: Jogo):
        if not self.server.partida.iniciar(jogo):
            return self._json({"erro": "já tem um jogo aberto"}, HTTPStatus.CONFLICT)
        return self._json({"jogando": jogo.id})

    def _instalar(self, jogo: Jogo):
        if _epic_pelo_legendary(jogo):
            tamanho = downloads.epic_tamanho(jogo.extra["app"])
            livre = downloads.livre_em(downloads.pasta_epic())
            if tamanho and tamanho[1] > livre:
                return self._json(
                    {"erro": f"não cabe: precisa de {_gb(tamanho[1])} e o disco tem {_gb(livre)} livres"},
                    HTTPStatus.CONFLICT,
                )
            self.server.downloads.baixar_epic(jogo.id, jogo.extra["app"], jogo.nome)
            return self._json({"mensagem": "Baixando. Acompanhe na aba Downloads."})
        if jogo.origem in ("steam", "heroic"):
            return self._json({"mensagem": lojas.acao(jogo, "instalar")})
        if jogo.origem == "portmaster":
            if not self.server.tarefas.iniciar(jogo.id, portmaster.comando_instalar(jogo)):
                return self._json({"erro": "já está instalando"}, HTTPStatus.CONFLICT)
            return self._json({"mensagem": f"Instalando {jogo.nome} pelo PortMaster."})
        if jogo.origem == "rom":
            argv = [*_allgames(), "emuladores", "instalar", jogo.extra["sistema"]]
        else:
            argv = [*_allgames(), "instalar", jogo.id]
        if not self.server.tarefas.iniciar(jogo.id, argv):
            return self._json({"erro": "já está instalando"}, HTTPStatus.CONFLICT)
        return self._json({"mensagem": "Instalando no PC. Acompanhe em ~/AllGames/logs/instalacoes.log"})

    def _desinstalar(self, jogo: Jogo):
        if jogo.origem == "portmaster":
            self.server.tarefas.iniciar(jogo.id, portmaster.comando_desinstalar(jogo))
            return self._json({"mensagem": f"Desinstalando {jogo.nome}."})
        if _epic_pelo_legendary(jogo):
            argv = [*downloads.legendary(), "uninstall", jogo.extra["app"], "-y"]
            self.server.tarefas.iniciar(jogo.id, argv)
            return self._json({"mensagem": f"Desinstalando {jogo.nome}."})
        return self._json({"mensagem": lojas.acao(jogo, "desinstalar")})


def _epic_pelo_legendary(jogo: Jogo) -> bool:
    return jogo.origem == "heroic" and jogo.extra.get("runner") == "legendary" and bool(downloads.legendary())


def _gb(quantidade: int) -> str:
    return f"{quantidade / 1024**3:.1f} GB"


def _allgames() -> list[str]:
    return [sys.executable, str(caminhos.EXECUTAVEL)]


def comando_jogar(gamescope: bool):
    def comando(jogo: Jogo) -> list[str]:
        opcoes = ["--gamescope"] if gamescope else []
        return [*_allgames(), "jogar", *opcoes, jogo.id]

    return comando


def comando_navegador(url: str) -> list[str] | None:
    """Navegador em tela cheia, com um perfil só do portal."""
    perfil = caminhos.base() / "portal" / "navegador"
    perfil.mkdir(parents=True, exist_ok=True)
    edge = windows.edge() if windows.ATIVO and not os.environ.get("ALLGAMES_NAVEGADOR") else None
    if edge:
        # Perfil próprio: o Edge abre uma janela nova (e espera nela) em vez de passar para o já aberto.
        return [
            str(edge),
            f"--user-data-dir={perfil}",
            "--kiosk",
            url,
            "--edge-kiosk-type=fullscreen",
            "--no-first-run",
            "--autoplay-policy=no-user-gesture-required",
        ]
    escolhido = os.environ.get("ALLGAMES_NAVEGADOR")
    candidatos = [escolhido] if escolhido else NAVEGADORES
    for nome in candidatos:
        binario = shutil.which(nome)
        if not binario:
            continue
        if "firefox" in nome:
            _preparar_firefox(perfil)
            return [binario, "--kiosk", "--no-remote", "--profile", str(perfil), url]
        return [
            binario,
            f"--user-data-dir={perfil}",
            "--kiosk",
            f"--app={url}",
            "--no-first-run",
            "--noerrdialogs",
            "--disable-session-crashed-bubble",
            "--disable-translate",
            "--autoplay-policy=no-user-gesture-required",
        ]
    return None


def _preparar_firefox(perfil: Path) -> None:
    preferencias = {
        "browser.shell.checkDefaultBrowser": False,
        "browser.aboutwelcome.enabled": False,
        "browser.startup.homepage_override.mstone": "ignore",
        "browser.sessionstore.resume_from_crash": False,
        "datareporting.policy.dataSubmissionPolicyBypassNotification": True,
        "toolkit.telemetry.reportingpolicy.firstRun": False,
        "trailhead.firstrun.didSeeAboutWelcome": True,
        "dom.gamepad.enabled": True,
    }
    linhas = [f"user_pref({json.dumps(k)}, {json.dumps(v)});" for k, v in preferencias.items()]
    (perfil / "user.js").write_text("\n".join(linhas) + "\n")


def voltar_ao_portal(partida: Partida, controles=None, segurar: float = 1.0, parar=None) -> None:
    """Select+Start segurado fora dos jogos do AllGames (na Steam): fecha o Big Picture e o portal reaparece.

    Dentro dos jogos do AllGames quem sai com essa combinação é o emulador (ou o supervisor).
    Se a combinação começou com um jogo aberto, ela foi para o jogo: só vale de novo depois de soltar.
    """
    controles = controles or supervisor.novos_controles()
    desde = None
    do_jogo = False
    while not (parar and parar.is_set()):
        controles.ler(0.2)
        if not controles.combo_apertado():
            desde, do_jogo = None, False
            continue
        if do_jogo or partida.jogo:
            do_jogo = True
            continue
        desde = desde or time.monotonic()
        if time.monotonic() - desde >= segurar:
            lojas.fechar_big_picture()
            do_jogo = True  # espera soltar
    controles.fechar()


def servir(carregar_jogos, porta: int, publico: bool, kiosk: bool, gamescope: bool) -> int:
    navegador: subprocess.Popen | None = None

    def sair():
        if navegador and navegador.poll() is None:
            navegador.terminate()
        servidor.shutdown()

    endereco = ("0.0.0.0" if publico else "127.0.0.1", porta)
    servidor = Portal(endereco, carregar_jogos, comando_jogar(gamescope), ao_sair=sair if kiosk else None)
    url = f"http://127.0.0.1:{porta}/"

    if not kiosk:
        print(f"Portal em {url}" + (f" (e na rede, porta {porta})" if publico else "") + " — Ctrl+C para parar")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            servidor.partida.encerrar()
        return 0

    comando = comando_navegador(url)
    if not comando:
        print("Nenhum navegador encontrado (instale o Firefox ou o Chromium).", file=sys.stderr)
        return 1
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    threading.Thread(target=voltar_ao_portal, args=(servidor.partida,), daemon=True).start()
    navegador = subprocess.Popen(comando)
    navegador.wait()
    servidor.partida.encerrar()
    servidor.shutdown()
    return 0
