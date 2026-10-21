import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from allgames import caminhos, sunshine
from allgames.catalogo import Jogo


class Mesclar(unittest.TestCase):
    def test_preserva_apps_do_usuario_e_troca_os_nossos(self):
        atual = {
            "env": {"PATH": "$(PATH)"},
            "apps": [
                {"name": "Desktop", "image-path": "desktop.png"},
                {"name": "Velho", "cmd": "/outro/lugar/bin/allgames jogar velho"},
                {"name": "Steam", "detached": ["setsid steam"]},
            ],
        }
        novos = [
            {"name": "Zelda", "cmd": "/r/bin/allgames jogar soh"},
            {"name": "Mario", "cmd": "/r/bin/allgames jogar sm64"},
        ]
        resultado, conflitos = sunshine.mesclar(atual, novos)
        self.assertEqual(conflitos, [])
        self.assertEqual([a["name"] for a in resultado["apps"]], ["Desktop", "Steam", "Mario", "Zelda"])
        self.assertEqual(resultado["env"], atual["env"])

    def test_nao_sobrescreve_app_do_usuario_com_mesmo_nome(self):
        atual = {"apps": [{"name": "Mario", "cmd": "meu-mario"}]}
        resultado, conflitos = sunshine.mesclar(atual, [{"name": "Mario", "cmd": "allgames jogar sm64"}])
        self.assertEqual(conflitos, ["Mario"])
        self.assertEqual(resultado["apps"], [{"name": "Mario", "cmd": "meu-mario"}])

    def test_reconhece_caminho_com_espacos(self):
        self.assertTrue(sunshine.eh_nosso({"cmd": '"/home/a b/bin/allgames" jogar --gamescope sm64'}))
        self.assertFalse(sunshine.eh_nosso({"cmd": "setsid steam"}))
        self.assertFalse(sunshine.eh_nosso({"name": "Desktop"}))


class AppDoJogo(unittest.TestCase):
    def test_campos(self):
        app = sunshine.app_do_jogo(Jogo("sm64", "Super Mario 64", "N64", "port"), Path("/c/sm64.png"), gamescope=True)
        self.assertEqual(app["name"], "Super Mario 64")
        self.assertTrue(app["cmd"].endswith("jogar --gamescope sm64"))
        self.assertEqual(app["image-path"], "/c/sm64.png")
        self.assertTrue(sunshine.eh_nosso(app))


class AppDoPortal(unittest.TestCase):
    def test_portal_e_reconhecido_como_nosso(self):
        app = sunshine.app_do_portal(gamescope=True)
        self.assertEqual(app["name"], "AllGames")
        self.assertTrue(app["cmd"].endswith("portal --kiosk --gamescope"))
        self.assertTrue(app["image-path"].endswith("portal/capa.png"))
        self.assertTrue(sunshine.eh_nosso(app))


class Arquivo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["XDG_CONFIG_HOME"] = self.tmp.name
        self.pasta = caminhos.config_sunshine()
        self.pasta.mkdir()

    def tearDown(self):
        os.environ.pop("XDG_CONFIG_HOME")
        self.tmp.cleanup()

    def test_padrao(self):
        self.assertEqual(sunshine.arquivo_apps(), self.pasta / "apps.json")

    def test_file_apps_do_sunshine_conf(self):
        (self.pasta / "sunshine.conf").write_text("port = 47989\nfile_apps = meus-apps.json\n")
        self.assertEqual(sunshine.arquivo_apps(), self.pasta / "meus-apps.json")

    def test_gravar_faz_backup(self):
        arquivo = self.pasta / "apps.json"
        self.assertIsNone(sunshine.gravar(arquivo, sunshine.ler(arquivo)))
        backup = sunshine.gravar(arquivo, {"apps": []})
        self.assertEqual(json.loads(backup.read_text())["apps"][0]["name"], "Desktop")
        self.assertEqual(json.loads(arquivo.read_text()), {"apps": []})


class Servico(unittest.TestCase):
    def _systemctl(self, ativo):
        def run(argv, **_):
            return mock.Mock(stdout="active\n" if argv[-1] == ativo else "inactive\n", returncode=0)

        return mock.patch("subprocess.run", side_effect=run)

    def test_sunshine_do_docker(self):
        with (
            mock.patch("shutil.which", return_value="/usr/bin/systemctl"),
            self._systemctl(sunshine.SERVICO_DOCKER) as run,
        ):
            self.assertEqual(sunshine.servico_ativo(), sunshine.SERVICO_DOCKER)
            self.assertTrue(sunshine.reiniciar())
        self.assertEqual(run.call_args.args[0], ["systemctl", "restart", sunshine.SERVICO_DOCKER])

    def test_sunshine_do_usuario(self):
        with mock.patch("shutil.which", return_value="/usr/bin/systemctl"), self._systemctl("sunshine") as run:
            self.assertTrue(sunshine.reiniciar())
        self.assertEqual(run.call_args.args[0], ["systemctl", "--user", "restart", "sunshine"])


if __name__ == "__main__":
    unittest.main()
