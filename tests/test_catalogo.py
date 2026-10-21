import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from allgames import caminhos, catalogo


class CatalogoReal(unittest.TestCase):
    def test_todo_jogo_tem_receita_com_instalar_e_executar(self):
        lib = caminhos.RECEITAS / "_lib.sh"
        for jogo in catalogo.carregar():
            with self.subTest(jogo=jogo.id):
                self.assertTrue(jogo.receita.exists(), f"falta {jogo.receita}")
                script = f'source "{lib}"; source "{jogo.receita}"; declare -F instalar executar'
                saida = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
                self.assertEqual(saida.returncode, 0, saida.stderr)

    def test_hashes_sao_sha1(self):
        for jogo in catalogo.carregar():
            for original in jogo.originais:
                for h in original.sha1:
                    self.assertRegex(h, r"^[0-9a-f]{40}$", jogo.id)


class Verificacao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ALLGAMES_HOME"] = self.tmp.name
        caminhos.originais().mkdir(parents=True)

    def tearDown(self):
        os.environ.pop("ALLGAMES_HOME")
        self.tmp.cleanup()

    def _jogo(self, **original):
        return catalogo.Jogo("x", "X", "N64", "port", originais=[catalogo.Original(**original)])

    def test_falta_arquivo(self):
        (resultado,) = catalogo.verificar(self._jogo(arquivo="rom.z64"))
        self.assertFalse(resultado.ok)
        self.assertIsNone(resultado.caminho)

    def test_opcional_ausente_nao_e_problema(self):
        (resultado,) = catalogo.verificar(self._jogo(arquivo="DIABDAT.MPQ", opcional=True))
        self.assertTrue(resultado.ok)

    def test_curinga_sem_diferenciar_maiusculas(self):
        (caminhos.originais() / "Metroid-Prime.RVZ").write_bytes(b"disco")
        (resultado,) = catalogo.verificar(self._jogo(arquivo="metroid-prime.*"))
        self.assertTrue(resultado.ok)
        self.assertEqual(resultado.caminho.name, "Metroid-Prime.RVZ")

    def test_sha1(self):
        (caminhos.originais() / "rom.z64").write_bytes(b"abc")
        certo = "a9993e364706816aba3e25717850c26c9cd0d89d"  # SHA-1 de "abc"
        self.assertTrue(catalogo.verificar(self._jogo(arquivo="rom.z64", sha1=[certo]))[0].ok)
        errado = catalogo.verificar(self._jogo(arquivo="rom.z64", sha1=["0" * 40]))[0]
        self.assertIn("SHA-1", errado.problema)


class Validacao(unittest.TestCase):
    def _carregar(self, toml: str):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(toml)
        try:
            return catalogo.carregar(Path(f.name))
        finally:
            os.unlink(f.name)

    def test_id_repetido(self):
        jogo = '[[jogo]]\nid="a"\nnome="A"\nplataforma="P"\ntipo="port"\n'
        with self.assertRaisesRegex(catalogo.ErroCatalogo, "repetido"):
            self._carregar(jogo * 2)

    def test_tipo_invalido(self):
        with self.assertRaisesRegex(catalogo.ErroCatalogo, "tipo"):
            self._carregar('[[jogo]]\nid="a"\nnome="A"\nplataforma="P"\ntipo="x"\n')

    def test_campo_desconhecido(self):
        with self.assertRaisesRegex(catalogo.ErroCatalogo, "inválida"):
            self._carregar('[[jogo]]\nid="a"\nnome="A"\nplataforma="P"\ntipo="port"\ncor="azul"\n')


if __name__ == "__main__":
    unittest.main()
