import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from allgames import portal
from allgames.catalogo import Jogo


class Portal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ALLGAMES_HOME"] = self.tmp.name
        self.instalado = Jogo("a", "Jogo A", "GBA", "emulador", colecao="Pokémon", saves=["*.sav"])
        self.instalado.pasta.mkdir(parents=True)
        (self.instalado.pasta / ".instalado").touch()
        (self.instalado.pasta / "a.sav").write_text("save")
        self.pendente = Jogo("b", "Jogo B", "PC", "pc", controles=["toque"])
        comando = lambda jogo: [sys.executable, "-c", "import time; time.sleep(30)"]  # noqa: E731
        self.servidor = portal.Portal(("127.0.0.1", 0), [self.instalado, self.pendente], comando)
        self.url = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def tearDown(self):
        self.servidor.partida.encerrar()
        self.servidor.shutdown()
        self.servidor.server_close()
        os.environ.pop("ALLGAMES_HOME")
        self.tmp.cleanup()

    def _pedir(self, caminho, metodo="GET", cabecalho=True):
        pedido = urllib.request.Request(self.url + caminho, method=metodo)
        if cabecalho:
            pedido.add_header("X-AllGames", "1")
        try:
            with urllib.request.urlopen(pedido, timeout=5) as resposta:
                return resposta.status, resposta.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_pagina_e_lista_de_jogos(self):
        status, corpo = self._pedir("/")
        self.assertEqual(status, 200)
        self.assertIn(b"AllGames", corpo)
        status, corpo = self._pedir("/api/jogos")
        dados = json.loads(corpo)
        a, b = dados["jogos"]
        self.assertTrue(a["instalado"])
        self.assertEqual(a["colecao"], "Pokémon")
        self.assertIsNotNone(a["ultimo_save"])
        self.assertFalse(b["instalado"])
        self.assertEqual(b["controles"], ["toque"])
        self.assertIsNone(dados["jogando"])

    def test_post_sem_cabecalho_e_recusado(self):
        status, _ = self._pedir("/api/jogar/a", "POST", cabecalho=False)
        self.assertEqual(status, 403)

    def test_jogar_um_por_vez_e_encerrar(self):
        self.assertEqual(self._pedir("/api/jogar/b", "POST")[0], 409)  # não instalado
        self.assertEqual(self._pedir("/api/jogar/zzz", "POST")[0], 404)
        self.assertEqual(self._pedir("/api/jogar/a", "POST")[0], 200)
        self.assertEqual(json.loads(self._pedir("/api/estado")[1])["jogando"], "a")
        self.assertEqual(self._pedir("/api/jogar/a", "POST")[0], 409)  # já tem jogo aberto
        self.assertEqual(self._pedir("/api/encerrar", "POST")[0], 200)
        time.sleep(0.2)
        self.assertIsNone(json.loads(self._pedir("/api/estado")[1])["jogando"])

    def test_sair_so_no_modo_kiosk(self):
        self.assertEqual(self._pedir("/api/sair", "POST")[0], 404)

    def test_capa_inexistente(self):
        self.assertEqual(self._pedir("/capas/b.png")[0], 404)
        self.assertEqual(self._pedir("/capas/../../etc/passwd.png")[0], 404)


if __name__ == "__main__":
    unittest.main()
