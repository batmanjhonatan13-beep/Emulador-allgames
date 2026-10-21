import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from allgames import capas
from allgames.capas import montar_indice, procurar, url_libretro
from allgames.catalogo import Jogo


class UrlLibretro(unittest.TestCase):
    def test_monta_url(self):
        self.assertEqual(
            url_libretro("Nintendo - Nintendo 64/Super Mario 64 (USA)"),
            "https://raw.githubusercontent.com/libretro-thumbnails/Nintendo_-_Nintendo_64"
            "/master/Named_Boxarts/Super%20Mario%2064%20%28USA%29.png",
        )

    def test_troca_caracteres_proibidos(self):
        self.assertIn("Sonic%20_%20Knuckles", url_libretro("Sega - Mega Drive - Genesis/Sonic & Knuckles"))
        self.assertIn("Majora%27s", url_libretro("Nintendo - Nintendo 64/Legend of Zelda, The - Majora's Mask (USA)"))


ACERVO = [
    "GoldenEye 007 (USA)",
    "GoldenEye 007 (Europe)",
    "GoldenEye 007 (Japan)",
    "Super Mario World (USA)",
    "Super Mario World (Japan)",
    "Super Mario World (USA) (Beta)",
    "7th Saga, The (USA)",
    "Pokemon - Black Version (USA, Europe) (NDS)",
    "Legend of Zelda, The - Link's Awakening (USA, Europe)",
    "Sonic _ Knuckles (World)",
    "Zoop (USA)",
]


class NomeParecido(unittest.TestCase):
    def setUp(self):
        self.indice = montar_indice(ACERVO)

    def achar(self, *nomes):
        return procurar(self.indice, list(nomes))

    def test_nomes_do_r36s_acham_a_capa_americana(self):
        self.assertEqual(self.achar("007 - GoldenEye"), "GoldenEye 007 (USA)")
        self.assertEqual(self.achar("002 Super Mario World"), "Super Mario World (USA)")
        self.assertEqual(self.achar("Zoop"), "Zoop (USA)")
        self.assertEqual(self.achar("Pokémon - Black Version"), "Pokemon - Black Version (USA, Europe) (NDS)")
        self.assertEqual(self.achar("The 7th Saga"), "7th Saga, The (USA)")
        self.assertEqual(
            self.achar("Legend of Zelda, The - Link's Awakening (U) [!]"),
            "Legend of Zelda, The - Link's Awakening (USA, Europe)",
        )
        self.assertEqual(self.achar("Sonic & Knuckles"), "Sonic _ Knuckles (World)")

    def test_usa_o_nome_do_emulationstation_quando_o_do_arquivo_nao_acha(self):
        self.assertIsNone(self.achar("sm64x"))
        self.assertEqual(self.achar("sm64x", "Super Mario World"), "Super Mario World (USA)")


class CapaLocal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ALLGAMES_HOME"] = self.tmp.name

    def tearDown(self):
        os.environ.pop("ALLGAMES_HOME")
        self.tmp.cleanup()

    def test_imagem_do_arkos_vem_antes_do_acervo(self):
        imagem = Path(self.tmp.name) / "roms/snes/downloaded_images/Zoop.jpg"
        imagem.parent.mkdir(parents=True)
        imagem.write_bytes(b"jpg")
        jogo = Jogo("rom:snes/Zoop.zip", "Zoop", "SNES", "emulador", capa="Nintendo - SNES/Zoop")
        jogo.extra = {"capa_local": str(imagem)}
        with mock.patch.object(capas, "_baixar") as baixar:
            self.assertEqual(capas.obter(jogo), imagem)
        baixar.assert_not_called()

    def test_baixa_a_capa_de_nome_parecido(self):
        jogo = Jogo("rom:n64/007 - GoldenEye.n64", "007 - GoldenEye", "N64", "emulador")
        jogo.capa = "Nintendo - Nintendo 64/007 - GoldenEye"
        with (
            mock.patch.object(capas, "_nomes_do_acervo", return_value=ACERVO),
            mock.patch.object(capas, "_baixar", return_value=capas.PNG + b"dados") as baixar,
        ):
            capas._indices.clear()
            destino = capas.obter(jogo)
        self.assertEqual(destino.read_bytes(), capas.PNG + b"dados")
        self.assertIn("GoldenEye%20007%20%28USA%29.png", baixar.call_args.args[0])
        self.assertIn("thumbnails.libretro.com", baixar.call_args.args[0])

    def test_sem_capa_no_acervo_nao_tenta_de_novo(self):
        jogo = Jogo("rom:n64/Inexistente.n64", "Inexistente", "N64", "emulador")
        jogo.capa = "Nintendo - Nintendo 64/Inexistente"
        with (
            mock.patch.object(capas, "_nomes_do_acervo", return_value=ACERVO),
            mock.patch.object(capas, "_baixar") as baixar,
        ):
            capas._indices.clear()
            self.assertIsNone(capas.obter(jogo))
            self.assertIsNone(capas.obter(jogo))
        baixar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
