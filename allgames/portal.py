"""Portal: a tela com as capas dos jogos, no estilo do Game Pass.

O portal é uma página web servida pelo próprio PC. No modo `--kiosk` ele abre um
navegador em tela cheia e vira um app do Sunshine ("AllGames"): você abre no
Moonlight, escolhe o jogo pela capa (tocando ou com o controle) e o jogo abre no
PC. Ao fechar o jogo, você volta para o portal.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import caminhos, capas, saves
from .catalogo import Jogo, verificar

PORTA = 47800
ARQUIVOS = {"/": "index.html", "/estilo.css": "estilo.css", "/app.js": "app.js"}
TIPOS_DE_ARQUIVO = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript"}
NAVEGADORES = ["chromium", "chromium-browser", "google-chrome", "brave-browser", "firefox"]
NOMES_DOS_TIPOS = {"port": "Port nativo", "recomp": "Recompilação", "emulador": "Emulador", "pc": "Jogo de PC"}


def _data(timestamp: float | None) -> str | None:
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds") if timestamp else None


def descrever(jogo: Jogo) -> dict:
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
        "capa": f"/capas/{jogo.id}.png" if jogo.capa or capas.obter(jogo, baixar=False) else None,
        "ultimo_save": _data(saves.ultimo_save(jogo)),
        "jogado_em": _data(jogo.jogado_em),
    }


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


class Portal(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, endereco, jogos: list[Jogo], comando, ao_sair=None):
        super().__init__(endereco, Handler)
        self.jogos = {j.id: j for j in jogos}
        self.partida = Partida(comando)
        self.ao_sair = ao_sair


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

    def do_GET(self):
        caminho = self.path.split("?")[0]
        if caminho in ARQUIVOS:
            arquivo = caminhos.PORTAL / ARQUIVOS[caminho]
            self._responder(HTTPStatus.OK, arquivo.read_bytes(), TIPOS_DE_ARQUIVO[arquivo.suffix])
        elif caminho == "/api/jogos":
            jogos = [descrever(j) for j in self.server.jogos.values()]
            self._json({"jogos": jogos, "jogando": self.server.partida.jogo, "pode_sair": bool(self.server.ao_sair)})
        elif caminho == "/api/estado":
            self._json({"jogando": self.server.partida.jogo})
        elif caminho.startswith("/capas/") and caminho.endswith(".png"):
            jogo = self.server.jogos.get(caminho[len("/capas/") : -len(".png")])
            capa = capas.obter(jogo) if jogo else None
            if capa:
                self._responder(HTTPStatus.OK, capa.read_bytes(), "image/png")
            else:
                self._responder(HTTPStatus.NOT_FOUND)
        else:
            self._responder(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        # Um site qualquer aberto no navegador não consegue mandar este cabeçalho
        # para cá (bloqueado pelo CORS), então só a própria página abre jogos.
        if self.headers.get("X-AllGames") != "1":
            return self._responder(HTTPStatus.FORBIDDEN)
        caminho = self.path.split("?")[0]
        if caminho.startswith("/api/jogar/"):
            jogo = self.server.jogos.get(caminho[len("/api/jogar/") :])
            if not jogo:
                return self._json({"erro": "jogo desconhecido"}, HTTPStatus.NOT_FOUND)
            if not jogo.instalado:
                return self._json({"erro": f"instale no PC: allgames instalar {jogo.id}"}, HTTPStatus.CONFLICT)
            if not self.server.partida.iniciar(jogo):
                return self._json({"erro": "já tem um jogo aberto"}, HTTPStatus.CONFLICT)
            self._json({"jogando": jogo.id})
        elif caminho == "/api/encerrar":
            self.server.partida.encerrar()
            self._json({"jogando": None})
        elif caminho == "/api/sair" and self.server.ao_sair:
            self._json({"saindo": True})
            self.server.partida.encerrar()
            threading.Thread(target=self.server.ao_sair, daemon=True).start()
        else:
            self._responder(HTTPStatus.NOT_FOUND)


def comando_jogar(gamescope: bool):
    def comando(jogo: Jogo) -> list[str]:
        opcoes = ["--gamescope"] if gamescope else []
        return [sys.executable, str(caminhos.EXECUTAVEL), "jogar", *opcoes, jogo.id]

    return comando


def comando_navegador(url: str) -> list[str] | None:
    """Navegador em tela cheia, com um perfil só do portal."""
    perfil = caminhos.base() / "portal" / "navegador"
    perfil.mkdir(parents=True, exist_ok=True)
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


def servir(jogos: list[Jogo], porta: int, publico: bool, kiosk: bool, gamescope: bool) -> int:
    navegador: subprocess.Popen | None = None

    def sair():
        if navegador and navegador.poll() is None:
            navegador.terminate()
        servidor.shutdown()

    endereco = ("0.0.0.0" if publico else "127.0.0.1", porta)
    servidor = Portal(endereco, jogos, comando_jogar(gamescope), ao_sair=sair if kiosk else None)
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
    navegador = subprocess.Popen(comando)
    navegador.wait()
    servidor.partida.encerrar()
    servidor.shutdown()
    return 0
