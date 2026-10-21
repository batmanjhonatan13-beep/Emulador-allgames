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
                self.assertTrue(jogo.arquivo_receita.exists(), f"falta {jogo.arquivo_receita}")
                script = f'source "{lib}"; source "{jogo.arquivo_receita}"; declare -F instalar executar'
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

    def test_acha_a_rom_certa_pelo_hash_qualquer_que_seja_o_nome(self):
        (caminhos.originais() / "Pokemon - Ruby.gba").write_bytes(b"ruby")
        (caminhos.originais() / "minha rom.GBA").write_bytes(b"abc")
        (caminhos.originais() / "jogo.gbc").write_bytes(b"gbc")
        certo = "a9993e364706816aba3e25717850c26c9cd0d89d"
        (resultado,) = catalogo.verificar(self._jogo(arquivo="*.gba", sha1=[certo]))
        self.assertEqual(resultado.caminho.name, "minha rom.GBA")
        (resultado,) = catalogo.verificar(self._jogo(arquivo="*.gb|*.gbc"))
        self.assertEqual(resultado.caminho.name, "jogo.gbc")

    def test_cache_de_sha1(self):
        rom = caminhos.originais() / "rom.z64"
        rom.write_bytes(b"abc")
        self.assertEqual(catalogo.sha1(rom), "a9993e364706816aba3e25717850c26c9cd0d89d")
        self.assertTrue((caminhos.base() / ".sha1-cache.json").exists())
        rom.write_bytes(b"abcd")  # tamanho mudou: calcula de novo
        self.assertEqual(catalogo.sha1(rom), "81fe8bfe87576c3ecb22426f8e57847382917acf")


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

    def test_padroes_da_receita(self):
        toml = (
            '[receita.mgba]\ntipo="emulador"\ncolecao="Pokémon"\nsaves=["*.sav"]\n'
            '[[jogo]]\nid="a"\nnome="A"\nplataforma="GBA"\nreceita="mgba"\n'
            '[[jogo]]\nid="b"\nnome="B"\nplataforma="GBA"\nreceita="mgba"\ncolecao="Outra"\n'
        )
        a, b = self._carregar(toml)
        self.assertEqual((a.tipo, a.colecao, a.saves), ("emulador", "Pokémon", ["*.sav"]))
        self.assertEqual(b.colecao, "Outra")
        self.assertEqual(a.arquivo_receita.name, "mgba.sh")

    def test_controles_invalidos(self):
        with self.assertRaisesRegex(catalogo.ErroCatalogo, "controles"):
            self._carregar('[[jogo]]\nid="a"\nnome="A"\nplataforma="P"\ntipo="port"\ncontroles=["teclado"]\n')

    def test_campo_desconhecido(self):
        with self.assertRaisesRegex(catalogo.ErroCatalogo, "inválida"):
            self._carregar('[[jogo]]\nid="a"\nnome="A"\nplataforma="P"\ntipo="port"\ncor="azul"\n')


if __name__ == "__main__":
    unittest.main()
