"""Roda um emulador e fecha ele quando você segura Select+Start, como no R36S.

O RetroArch já faz isso sozinho (e salva o estado). Os emuladores avulsos
(Eden, Azahar, xemu, ports do PortMaster) não têm esse atalho, então o
AllGames lê o controle direto do kernel (/dev/input/event*) e fecha o emulador
com calma quando a combinação fica apertada por um instante.
"""

import ctypes
import glob
import os
import select
import signal
import struct
import subprocess
import sys
import time

EV_KEY = 1
BTN_SELECT = 314
BTN_START = 315
COMBO = {BTN_SELECT, BTN_START}
# struct input_event: timeval (2 x long), type (u16), code (u16), value (s32)
EVENTO = struct.Struct("llHHi")


class Controles:
    """Lê os botões de todos os controles, inclusive os conectados depois."""

    def __init__(self, padrao: str = "/dev/input/event*"):
        self.padrao = padrao
        self.abertos: dict[str, int] = {}
        self.apertados: dict[str, set[int]] = {}
        self._ultima_busca = 0.0

    def buscar(self) -> None:
        self._ultima_busca = time.monotonic()
        for caminho in glob.glob(self.padrao):
            if caminho in self.abertos:
                continue
            try:
                self.abertos[caminho] = os.open(caminho, os.O_RDONLY | os.O_NONBLOCK)
                self.apertados[caminho] = set()
            except OSError:
                continue  # sem permissão ou não é um dispositivo de entrada

    def _fechar(self, caminho: str) -> None:
        os.close(self.abertos.pop(caminho))
        self.apertados.pop(caminho, None)

    def ler(self, espera: float) -> None:
        if time.monotonic() - self._ultima_busca > 2:
            self.buscar()
        if not self.abertos:
            time.sleep(espera)
            return
        prontos, _, _ = select.select(list(self.abertos.values()), [], [], espera)
        for caminho, fd in list(self.abertos.items()):
            if fd not in prontos:
                continue
            try:
                dados = os.read(fd, EVENTO.size * 64)
            except BlockingIOError:
                continue
            except OSError:
                self._fechar(caminho)  # controle desconectado
                continue
            for inicio in range(0, len(dados) - EVENTO.size + 1, EVENTO.size):
                _, _, tipo, codigo, valor = EVENTO.unpack_from(dados, inicio)
                if tipo == EV_KEY and codigo in COMBO:
                    if valor:
                        self.apertados[caminho].add(codigo)
                    else:
                        self.apertados[caminho].discard(codigo)

    def combo_apertado(self) -> bool:
        return any(COMBO <= botoes for botoes in self.apertados.values())

    def fechar(self) -> None:
        for caminho in list(self.abertos):
            self._fechar(caminho)


class _XInputGamepad(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XInputState(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_uint), ("Gamepad", _XInputGamepad)]


class ControlesXInput:
    """O mesmo que Controles, no Windows: lê os controles XInput (o do Sunshine é um deles)."""

    BACK = 0x0020
    START = 0x0010

    def __init__(self, dll=None):
        self._dll = dll
        if self._dll is None:
            for nome in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
                try:
                    self._dll = ctypes.WinDLL(nome)  # type: ignore[attr-defined]
                    break
                except (AttributeError, OSError):
                    continue
        self._apertado = False

    def buscar(self) -> None:
        pass

    def ler(self, espera: float) -> None:
        time.sleep(espera)
        self._apertado = False
        if not self._dll:
            return
        estado = _XInputState()
        for indice in range(4):
            if self._dll.XInputGetState(indice, ctypes.byref(estado)) == 0:
                botoes = estado.Gamepad.wButtons
                if botoes & self.BACK and botoes & self.START:
                    self._apertado = True

    def combo_apertado(self) -> bool:
        return self._apertado

    def fechar(self) -> None:
        pass


def novos_controles():
    """Leitor de controles do sistema: /dev/input no Linux, XInput no Windows."""
    return ControlesXInput() if sys.platform == "win32" else Controles()


def encerrar(processo: subprocess.Popen, espera: float = 10) -> None:
    """Pede para fechar (SIGTERM) e, se não fechar a tempo, força."""
    if processo.poll() is not None:
        return
    processo.terminate()
    try:
        processo.wait(espera)
    except subprocess.TimeoutExpired:
        processo.kill()


def rodar(argv: list[str], env: dict | None = None, log=None, segurar: float = 1.0, controles=None) -> int:
    """Roda o comando e devolve o código de saída. Select+Start segurado fecha o programa."""
    processo = subprocess.Popen(argv, env=env, stdout=log, stderr=log)

    def repassar(sinal, _quadro):
        encerrar(processo)

    for nome in ("SIGTERM", "SIGINT", "SIGHUP"):  # o Windows não tem SIGHUP
        if hasattr(signal, nome):
            signal.signal(getattr(signal, nome), repassar)

    controles = controles or novos_controles()
    controles.buscar()
    desde = None
    try:
        while processo.poll() is None:
            controles.ler(0.2)
            if controles.combo_apertado():
                desde = desde or time.monotonic()
                if time.monotonic() - desde >= segurar:
                    encerrar(processo)
                    break
            else:
                desde = None
    finally:
        controles.fechar()
    return processo.wait()
