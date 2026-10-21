import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from allgames import portmaster

CATALOGO = {
    "ports": {
        "2048.zip": {
            "items": ["2048.sh", "2048/"],
            "source": {"url": "https://exemplo/2048.zip", "md5": ""},
            "attr": {
                "title": "2048",
                "desc": "Junte os números.",
                "arch": ["aarch64", "x86_64"],
                "rtr": True,
                "image": {"screenshot": "screenshot.png"},
                "runtime": None,
            },
        },
        "celeste.zip": {
            "items": ["Celeste.sh", "celeste/"],
            "attr": {
                "title": "Celeste",
                "avail": ["steamdeck:x86_64"],
                "rtr": False,
                "inst": "Copie os arquivos do jogo para ports/celeste/gamedata.",
            },
        },
        "so-arm.zip": {"items": ["SoArm.sh", "soarm/"], "attr": {"title": "Só ARM", "arch": ["aarch64"], "rtr": True}},
    }
}


def elf(maquina: int) -> bytes:
    return b"\x7fELF" + bytes(14) + maquina.to_bytes(2, "little") + bytes(40)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = Path(self.tmp.name)
        self.ferramentas = raiz / "PortMaster"
        self.ports = raiz / "ports"
        self.ferramentas.mkdir()
        self.ports.mkdir()
        (self.ferramentas / "harbourmaster").touch()
        self.env = mock.patch.dict(
            os.environ,
            {
                "ALLGAMES_PORTMASTER": str(self.ferramentas),
                "ALLGAMES_PORTS": str(self.ports),
                "ALLGAMES_HOME": str(raiz),
            },
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class Catalogo(Base):
    def test_so_os_ports_que_rodam_em_pc(self):
        self.assertTrue(portmaster.roda_aqui(CATALOGO["ports"]["2048.zip"]))
        self.assertTrue(portmaster.roda_aqui(CATALOGO["ports"]["celeste.zip"]))
        self.assertFalse(portmaster.roda_aqui(CATALOGO["ports"]["so-arm.zip"]))
        self.assertEqual([j.nome for j in portmaster.jogos(CATALOGO)], ["2048", "Celeste"])

    def test_instalado_e_aviso(self):
        (self.ports / "2048.sh").touch()
        (self.ports / "2048").mkdir()
        jogos = {j.id: j for j in portmaster.jogos(CATALOGO)}
        port, celeste = jogos["port:2048.zip"], jogos["port:celeste.zip"]
        self.assertTrue(port.instalado)
        self.assertEqual(port.acoes, ["jogar", "desinstalar"])
        self.assertEqual(port.origem, "portmaster")
        self.assertTrue(port.extra["combo_sair"])
        self.assertEqual(port.extra["aviso"], "")
        self.assertTrue(port.capa_url.endswith("/ports/2048/screenshot.png"))
        self.assertFalse(celeste.instalado)
        self.assertEqual(celeste.acoes, ["instalar"])
        self.assertIn("gamedata", celeste.extra["aviso"])

    def test_sem_portmaster_nao_mostra_nada(self):
        (self.ferramentas / "harbourmaster").unlink()
        self.assertEqual(portmaster.jogos(CATALOGO), [])


class Ambiente(Base):
    def test_troca_as_ferramentas_de_arm_pelas_do_pc(self):
        (self.ferramentas / "gptokeyb").write_bytes(elf(183))  # aarch64
        (self.ferramentas / "gptokeyb.x86_64").write_bytes(elf(62))
        (self.ferramentas / "xdelta3").write_bytes(elf(62))  # já é do PC: fica como está
        (self.ferramentas / "xdelta3.x86_64").write_bytes(elf(62) + b"outro")
        portmaster.preparar_ambiente()
        self.assertEqual((self.ferramentas / "gptokeyb").read_bytes(), elf(62))
        self.assertTrue(os.access(self.ferramentas / "gptokeyb", os.X_OK))
        self.assertEqual((self.ferramentas / "xdelta3").read_bytes(), elf(62))
        self.assertEqual((self.ferramentas / "mod_Unknown.txt").read_text(), portmaster.MOD_PC)
        self.assertTrue((self.ferramentas / f"mod_{portmaster.nome_da_plataforma()}.txt").exists())

    @unittest.skipUnless(shutil.which("bash"), "precisa do bash")
    def test_mod_usa_o_controle_do_sunshine(self):
        mod = self.ferramentas / "mod_Unknown.txt"
        mod.write_text(portmaster.MOD_PC)
        script = f'get_controls() {{ echo "$1|$2"; }}; source "{mod}"; source "{mod}"; get_controls; get_controls a b'
        saida = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
        self.assertEqual(saida.splitlines(), ["030000005e0400008e02000010010000|allgames", "a|b"])


class Instalar(Base):
    def _catalogo(self, md5):
        dados = {"ports": {"2048.zip": {**CATALOGO["ports"]["2048.zip"], "source": {"url": "u", "md5": md5}}}}
        return mock.patch.object(portmaster, "catalogo", return_value=dados)

    def test_confere_o_md5_e_instala_sem_internet(self):
        conteudo = b"zip do port"
        resposta = mock.mock_open(read_data=conteudo)
        with (
            self._catalogo(hashlib.md5(conteudo).hexdigest()),
            mock.patch("urllib.request.urlopen", resposta),
            mock.patch.object(portmaster, "_rodar_harbourmaster") as rodar,
        ):
            portmaster.instalar("2048.zip")
        argv = rodar.call_args.args[0]
        self.assertEqual(argv[-3:-1], ["install", str(Path(self.tmp.name) / ".cache-ports/2048.zip")])
        self.assertEqual(argv[-1], "--offline")
        self.assertFalse((Path(self.tmp.name) / ".cache-ports/2048.zip").exists(), "o zip baixado é apagado")

    def test_arquivo_corrompido(self):
        with (
            self._catalogo("0" * 32),
            mock.patch("urllib.request.urlopen", mock.mock_open(read_data=b"outro")),
            mock.patch.object(portmaster, "_rodar_harbourmaster") as rodar,
        ):
            with self.assertRaisesRegex(RuntimeError, "MD5"):
                portmaster.instalar("2048.zip")
        rodar.assert_not_called()

    def test_port_fora_do_catalogo(self):
        with self._catalogo(""), self.assertRaises(ValueError):
            portmaster.instalar("nao-existe.zip")

    def test_harbourmaster_roda_dentro_da_pasta_dele(self):
        with mock.patch("subprocess.run") as run:
            portmaster.desinstalar("2048.zip")
        self.assertEqual(run.call_args.kwargs["cwd"], self.ferramentas)
        self.assertEqual(run.call_args.args[0][-2:], ["uninstall", "2048.zip"])


if __name__ == "__main__":
    unittest.main()
