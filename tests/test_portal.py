import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

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
        jogos = [self.instalado, self.pendente]
        self.servidor = portal.Portal(("127.0.0.1", 0), lambda: jogos, comando)
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
        status, _ = self._pedir("/api/jogar?id=a", "POST", cabecalho=False)
        self.assertEqual(status, 403)

    def test_jogar_um_por_vez_e_encerrar(self):
        self.assertEqual(self._pedir("/api/jogar?id=b", "POST")[0], 409)  # não instalado
        self.assertEqual(self._pedir("/api/jogar?id=zzz", "POST")[0], 404)
        self.assertEqual(self._pedir("/api/jogar?id=a", "POST")[0], 200)
        self.assertEqual(json.loads(self._pedir("/api/estado")[1])["jogando"], "a")
        self.assertEqual(self._pedir("/api/jogar?id=a", "POST")[0], 409)  # já tem jogo aberto
        self.assertEqual(self._pedir("/api/encerrar", "POST")[0], 200)
        time.sleep(0.2)
        self.assertIsNone(json.loads(self._pedir("/api/estado")[1])["jogando"])

    def test_sair_so_no_modo_kiosk(self):
        self.assertEqual(self._pedir("/api/sair", "POST")[0], 404)

    def test_capa_inexistente(self):
        self.assertEqual(self._pedir("/capa?id=b")[0], 404)
        self.assertEqual(self._pedir("/capa?id=../../etc/passwd")[0], 404)

    def test_downloads_e_discos(self):
        status, corpo = self._pedir("/api/downloads")
        dados = json.loads(corpo)
        self.assertEqual(status, 200)
        self.assertIsInstance(dados["downloads"], list)
        self.assertTrue(all(d["livre"] <= d["total"] for d in dados["discos"]))
        status, corpo = self._pedir("/api/download?id=epic:nada&acao=pausar", "POST")
        self.assertEqual(status, 409)
        self.assertIn("não encontrado", json.loads(corpo)["erro"])
        self.assertEqual(self._pedir("/api/download?id=epic:nada&acao=pausar", "POST", cabecalho=False)[0], 403)

    def test_acoes(self):
        jogos = {j["id"]: j for j in json.loads(self._pedir("/api/jogos")[1])["jogos"]}
        self.assertEqual(jogos["a"]["acoes"], ["jogar"])
        self.assertEqual(jogos["b"]["acoes"], ["instalar"])  # sem originais exigidos
        self.assertEqual(jogos["a"]["origem"], "catalogo")
        self.assertEqual(self._pedir("/api/desinstalar?id=a", "POST")[0], 409)


class JogoNovoAparece(unittest.TestCase):
    def test_versao_muda_quando_entra_um_jogo_nas_pastas(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"ALLGAMES_HOME": tmp}):
            roms = portal.sistemas.roms_dir()
            (roms / "snes/hacks").mkdir(parents=True)
            antes = portal.versao_da_biblioteca()
            self.assertEqual(portal.versao_da_biblioteca(), antes, "nada mudou")
            (roms / "snes/Zoop.sfc").write_bytes(b"rom")
            depois = portal.versao_da_biblioteca()
            self.assertNotEqual(depois, antes)
            (roms / "snes/hacks/Mario Hack.sfc").write_bytes(b"rom")
            self.assertNotEqual(portal.versao_da_biblioteca(), depois, "jogo numa subpasta também conta")


class ControlesDeMentira:
    """Sequência de leituras: cada item diz se Select+Start está apertado naquele instante."""

    def __init__(self, sequencia, relogio):
        self.sequencia = list(sequencia)
        self.relogio = relogio
        self.atual = False

    def ler(self, espera):
        self.relogio[0] += espera
        self.atual = self.sequencia.pop(0) if self.sequencia else False

    def combo_apertado(self):
        return self.atual

    def fechar(self):
        pass


class VoltarAoPortal(unittest.TestCase):
    def rodar(self, sequencia, jogando_ate=0):
        relogio = [0.0]
        controles = ControlesDeMentira(sequencia, relogio)
        parar = threading.Event()
        partida = mock.Mock()
        type(partida).jogo = mock.PropertyMock(side_effect=lambda: "rom:x" if relogio[0] <= jogando_ate else None)
        leituras = len(sequencia)

        def ler(espera):
            ControlesDeMentira.ler(controles, espera)
            if not controles.sequencia and leituras:
                parar.set()

        controles.ler = ler
        with (
            mock.patch.object(portal.lojas, "fechar_big_picture") as fechar,
            mock.patch.object(portal.time, "monotonic", side_effect=lambda: relogio[0]),
        ):
            portal.voltar_ao_portal(partida, controles, segurar=1.0, parar=parar)
        return fechar.call_count

    def test_segurar_select_start_na_steam_volta_para_o_portal(self):
        self.assertEqual(self.rodar([True] * 8 + [False]), 1)

    def test_apertar_rapido_nao_faz_nada(self):
        self.assertEqual(self.rodar([True, True, False, True, False]), 0)

    def test_sair_do_emulador_com_o_combo_nao_fecha_a_steam(self):
        # O combo começou com o jogo aberto (o emulador fecha) e continua apertado depois.
        self.assertEqual(self.rodar([True] * 12 + [False], jogando_ate=0.6), 0)


if __name__ == "__main__":
    unittest.main()
