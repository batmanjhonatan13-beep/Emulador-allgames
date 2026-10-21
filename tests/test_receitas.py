import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from allgames import caminhos, receitas
from allgames.catalogo import Jogo, Original

RECEITA = """
instalar() { echo "rom=$ORIGINAL" > "$JOGO_DIR/instalado.txt"; }
executar() { echo "jogando $JOGO_ID de $JOGO_DIR"; }
"""


class Receitas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = Path(self.tmp.name)
        os.environ["ALLGAMES_HOME"] = str(raiz / "home")
        self.receitas_originais = caminhos.RECEITAS
        caminhos.RECEITAS = raiz / "receitas"
        caminhos.RECEITAS.mkdir()
        shutil.copy(self.receitas_originais / "_lib.sh", caminhos.RECEITAS)
        (caminhos.RECEITAS / "teste.sh").write_text(RECEITA)
        caminhos.originais().mkdir(parents=True)
        (caminhos.originais() / "Teste.Z64").write_bytes(b"rom")
        self.jogo = Jogo("teste", "Teste", "N64", "port", originais=[Original("teste.z64")])

    def tearDown(self):
        caminhos.RECEITAS = self.receitas_originais
        os.environ.pop("ALLGAMES_HOME")
        self.tmp.cleanup()

    def test_instalar_passa_variaveis_e_marca_instalado(self):
        self.assertFalse(self.jogo.instalado)
        self.assertEqual(receitas.instalar(self.jogo), 0)
        self.assertTrue(self.jogo.instalado)
        texto = (self.jogo.pasta / "instalado.txt").read_text()
        self.assertEqual(texto.strip(), f"rom={caminhos.originais() / 'Teste.Z64'}")

    def test_falha_na_receita_nao_marca_instalado(self):
        (caminhos.RECEITAS / "teste.sh").write_text("instalar() { false; echo nunca; }\n")
        self.assertNotEqual(receitas.instalar(self.jogo), 0)
        self.assertFalse(self.jogo.instalado)

    def test_jogar_grava_log(self):
        argv, env = receitas.comando_jogar(self.jogo)
        self.assertEqual(argv[0], "bash")
        subprocess.run(argv, env=env, check=True)
        log = (caminhos.logs() / "teste.log").read_text()
        self.assertIn(f"jogando teste de {self.jogo.pasta}", log)

    def test_gamescope_usa_resolucao_do_celular(self):
        os.environ.update(SUNSHINE_CLIENT_WIDTH="2400", SUNSHINE_CLIENT_HEIGHT="1080", SUNSHINE_CLIENT_FPS="90")
        try:
            argv, _ = receitas.comando_jogar(self.jogo, gamescope=True)
        finally:
            for v in ("SUNSHINE_CLIENT_WIDTH", "SUNSHINE_CLIENT_HEIGHT", "SUNSHINE_CLIENT_FPS"):
                os.environ.pop(v)
        if shutil.which("gamescope"):
            self.assertEqual(argv[:9], ["gamescope", "-f", "-W", "2400", "-H", "1080", "-r", "90", "--"])
        else:
            self.assertEqual(argv[0], "bash")


if __name__ == "__main__":
    unittest.main()
