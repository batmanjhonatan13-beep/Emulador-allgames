import os
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path

from allgames import supervisor


def evento(codigo, valor, tipo=supervisor.EV_KEY):
    return supervisor.EVENTO.pack(0, 0, tipo, codigo, valor)


class Controles(unittest.TestCase):
    """Um FIFO faz o papel de /dev/input/eventN: mesmo formato de evento do kernel."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fifo = Path(self.tmp.name) / "event0"
        os.mkfifo(self.fifo)
        self.controles = supervisor.Controles(str(Path(self.tmp.name) / "event*"))
        self.controles.buscar()
        self.escrita = os.open(self.fifo, os.O_WRONLY)

    def tearDown(self):
        os.close(self.escrita)
        self.controles.fechar()
        self.tmp.cleanup()

    def _enviar(self, *eventos):
        os.write(self.escrita, b"".join(eventos))
        self.controles.ler(1)

    def test_select_e_start_juntos(self):
        self.assertIn(str(self.fifo), self.controles.abertos)
        self._enviar(evento(supervisor.BTN_SELECT, 1))
        self.assertFalse(self.controles.combo_apertado())
        self._enviar(evento(supervisor.BTN_START, 1))
        self.assertTrue(self.controles.combo_apertado())
        self._enviar(evento(supervisor.BTN_START, 0))
        self.assertFalse(self.controles.combo_apertado())

    def test_ignora_outros_botoes_e_eixos(self):
        self._enviar(evento(304, 1), evento(supervisor.BTN_START, 1, tipo=3), evento(supervisor.BTN_SELECT, 1))
        self.assertEqual(self.controles.apertados[str(self.fifo)], {supervisor.BTN_SELECT})


class ControlesFalsos:
    def __init__(self, apertado_depois=None):
        self.inicio = time.monotonic()
        self.apertado_depois = apertado_depois
        self.fechado = False

    def buscar(self):
        pass

    def ler(self, espera):
        time.sleep(0.05)

    def combo_apertado(self):
        return self.apertado_depois is not None and time.monotonic() - self.inicio >= self.apertado_depois

    def fechar(self):
        self.fechado = True


class Rodar(unittest.TestCase):
    def setUp(self):
        sinais = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        self.originais = {s: signal.getsignal(s) for s in sinais}

    def tearDown(self):
        for sinal, tratador in self.originais.items():
            signal.signal(sinal, tratador)

    def test_devolve_o_codigo_de_saida(self):
        controles = ControlesFalsos()
        codigo = supervisor.rodar([sys.executable, "-c", "raise SystemExit(3)"], controles=controles)
        self.assertEqual(codigo, 3)
        self.assertTrue(controles.fechado)

    def test_combo_segurado_fecha_o_emulador(self):
        inicio = time.monotonic()
        codigo = supervisor.rodar(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            segurar=0.2,
            controles=ControlesFalsos(apertado_depois=0.1),
        )
        self.assertEqual(codigo, -signal.SIGTERM)
        self.assertLess(time.monotonic() - inicio, 10)


if __name__ == "__main__":
    unittest.main()
