import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from allgames import caminhos, saves
from allgames.catalogo import Jogo


class Saves(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = Path(self.tmp.name)
        os.environ["ALLGAMES_HOME"] = str(raiz / "ag")
        self.home = raiz / "home"
        self.patch = mock.patch("pathlib.Path.home", return_value=self.home)
        self.patch.start()
        self.jogo = Jogo("x", "X", "GBA", "emulador", saves=["*.sav", "~/.local/share/x/*.dat"])
        self.jogo.pasta.mkdir(parents=True)
        (self.home / ".local/share/x").mkdir(parents=True)

    def tearDown(self):
        self.patch.stop()
        os.environ.pop("ALLGAMES_HOME")
        self.tmp.cleanup()

    def test_acha_saves_na_pasta_do_jogo_e_na_home(self):
        (self.jogo.pasta / "x.sav").write_text("a")
        (self.jogo.pasta / "x.gba").write_text("rom")
        (self.home / ".local/share/x/slot1.dat").write_text("b")
        nomes = [p.name for p in saves.arquivos(self.jogo)]
        self.assertEqual(sorted(nomes), ["slot1.dat", "x.sav"])
        self.assertIsNotNone(saves.ultimo_save(self.jogo))

    def test_sem_saves_nao_faz_backup(self):
        self.assertIsNone(saves.fazer_backup(self.jogo))
        self.assertIsNone(saves.ultimo_save(self.jogo))

    def test_backup_so_quando_muda_e_restaura(self):
        save = self.jogo.pasta / "x.sav"
        extra = self.home / ".local/share/x/slot1.dat"
        save.write_text("progresso 1")
        extra.write_text("extra 1")
        primeira = saves.fazer_backup(self.jogo)
        self.assertIsNotNone(primeira)
        self.assertIsNone(saves.fazer_backup(self.jogo), "nada mudou: não deve copiar de novo")

        save.write_text("progresso 2 (corrompido)")
        segunda = saves.fazer_backup(self.jogo)
        self.assertNotEqual(primeira, segunda)

        saves.restaurar(self.jogo, primeira)
        self.assertEqual(save.read_text(), "progresso 1")
        self.assertEqual(extra.read_text(), "extra 1")

    def test_guarda_so_as_ultimas_copias(self):
        save = self.jogo.pasta / "x.sav"
        with mock.patch.object(saves, "BACKUPS_POR_JOGO", 3):
            for i in range(5):
                save.write_text(f"v{i}")
                saves.fazer_backup(self.jogo)
        copias = saves.backups(self.jogo)
        self.assertEqual(len(copias), 3)
        self.assertEqual((copias[-1] / "jogo" / "x.sav").read_text(), "v4")

    def test_saves_de_roms_com_pasta_lida_uma_vez(self):
        """Mesmo resultado do glob, inclusive com colchetes no nome, lendo a pasta uma vez só."""
        import glob

        pasta = self.home / "roms/gb"
        pasta.mkdir(parents=True)
        nomes = [
            "Pokemon (USA) [!].gb",
            "Pokemon (USA) [!].srm",
            "Pokemon (USA) [!].state",
            "Pokemon (USA) [!].state1",
            "Pokemon (USA) [!] Hack.srm",
            "Pokemon (USA).srm",
            "Tetris.srm",
            ".Tetris.state",
        ]
        for nome in nomes:
            (pasta / nome).write_text("x")
        (pasta / "Pokemon (USA) [!].state.d").mkdir()
        padroes = ["{pasta_rom}/{nome}.srm", "{pasta_rom}/{nome}.state*", "{pasta_rom}/{nome}.sav"]
        pastas = saves.Pastas()
        with mock.patch("os.listdir", wraps=os.listdir) as listar:
            for rom in ("Pokemon (USA) [!].gb", "Tetris.gb", "Pokemon (USA).gb"):
                jogo = Jogo(f"rom:gb/{rom}", rom, "GB", "emulador")
                jogo.saves = [
                    p.replace("{pasta_rom}", glob.escape(str(pasta))).replace("{nome}", glob.escape(Path(rom).stem))
                    for p in padroes
                ]
                esperado = sorted({Path(p) for padrao in jogo.saves for p in glob.glob(padrao) if Path(p).is_file()})
                self.assertEqual(saves.arquivos(jogo, pastas), esperado, rom)
        self.assertEqual(listar.call_count, 1)
        jogo = Jogo("rom:gb/Pokemon (USA) [!].gb", "P", "GB", "emulador")
        jogo.saves = [f"{glob.escape(str(pasta))}/{glob.escape('Pokemon (USA) [!]')}.state*"]
        self.assertEqual(
            [p.name for p in saves.arquivos(jogo)], ["Pokemon (USA) [!].state", "Pokemon (USA) [!].state1"]
        )

    def test_pasta_dos_backups(self):
        (self.jogo.pasta / "x.sav").write_text("a")
        copia = saves.fazer_backup(self.jogo)
        self.assertEqual(copia.parent, caminhos.backups() / "x")
        self.assertTrue(copia.name.startswith(datetime.now().strftime("%Y%m%d")))


if __name__ == "__main__":
    unittest.main()
