import argparse
import contextlib
import io
import json
import os
import tempfile
import unittest

from allgames import caminhos, cli
from allgames.catalogo import Jogo


class Sincronizar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ALLGAMES_HOME"] = os.path.join(self.tmp.name, "ag")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, "cfg")
        self.jogos = [Jogo("teste", "Teste", "N64", "port")]
        self.jogos[0].pasta.mkdir(parents=True)
        (self.jogos[0].pasta / ".instalado").touch()

    def tearDown(self):
        os.environ.pop("ALLGAMES_HOME")
        os.environ.pop("XDG_CONFIG_HOME")
        self.tmp.cleanup()

    def _sincronizar(self, gamescope):
        with contextlib.redirect_stdout(io.StringIO()):
            cli.cmd_sincronizar(self.jogos, argparse.Namespace(gamescope=gamescope, sem_reiniciar=True))
        apps = json.loads((caminhos.config_sunshine() / "apps.json").read_text())["apps"]
        return next(a["cmd"] for a in apps if a["name"] == "Teste")

    def test_gamescope_e_mantido_quando_nao_informado(self):
        self.assertNotIn("--gamescope", self._sincronizar(None))
        self.assertIn("--gamescope", self._sincronizar(True))
        self.assertIn("--gamescope", self._sincronizar(None))
        self.assertNotIn("--gamescope", self._sincronizar(False))
        self.assertNotIn("--gamescope", self._sincronizar(None))

    def test_parser(self):
        parser = cli.montar_parser()
        self.assertIsNone(parser.parse_args(["sincronizar"]).gamescope)
        self.assertTrue(parser.parse_args(["sincronizar", "--gamescope"]).gamescope)
        self.assertFalse(parser.parse_args(["sincronizar", "--no-gamescope"]).gamescope)


if __name__ == "__main__":
    unittest.main()
