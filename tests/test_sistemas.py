import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from allgames import saves, sistemas


class CatalogoDeSistemas(unittest.TestCase):
    def test_arquivo_real_e_valido(self):
        emuladores, lista = sistemas.carregar()
        ids = [s.id for s in lista]
        self.assertEqual(len(ids), len(set(ids)), "pasta repetida")
        pastas = [p.lower() for s in lista for p in [s.id, *s.pastas]]
        self.assertEqual(len(pastas), len(set(pastas)), "nome de pasta usado por dois sistemas")
        for sistema in lista:
            emulador = emuladores[sistema.emulador]
            self.assertTrue(emulador.flatpak or emulador.appimage, emulador.chave)
            self.assertEqual(bool(sistema.core), emulador.chave == "retroarch", sistema.id)
            self.assertTrue(all(e == e.lower() and not e.startswith(".") for e in sistema.extensoes), sistema.id)
        for nome in ("switch", "psx", "ps2", "xbox", "psp", "snes", "gba", "n64", "nds"):
            self.assertIn(nome, ids)


class Pastas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.patch = mock.patch("pathlib.Path.home", return_value=self.home)
        self.patch.start()
        os.environ.pop("ALLGAMES_HOME", None)
        self.roms = self.home / "AllGames/roms"
        self.dados = sistemas.carregar()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def _rom(self, caminho, conteudo="x"):
        arquivo = self.roms / caminho
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(conteudo)
        return arquivo

    def test_pastas_do_arkos_e_nomes_alternativos(self):
        self._rom("megadrive/Sonic The Hedgehog (USA, Europe).md")
        self._rom("SNES/Super Mario World (USA) [!].sfc")
        self._rom("snes/LEIA-ME.txt")
        jogos = {j.id: j for j in sistemas.jogos(self.dados)}
        self.assertIn("rom:megadrive/Sonic The Hedgehog (USA, Europe).md", jogos)
        mario = jogos["rom:SNES/Super Mario World (USA) [!].sfc"]
        self.assertEqual(mario.nome, "Super Mario World")
        self.assertEqual(mario.plataforma, "Super Nintendo")
        self.assertEqual(mario.capa, "Nintendo - Super Nintendo Entertainment System/Super Mario World (USA) [!]")
        self.assertEqual(len(jogos), 2)

    def test_playlist_m3u_esconde_os_discos(self):
        self._rom("psx/FF7.m3u", "FF7 (Disc 1).chd\nFF7 (Disc 2).chd\n")
        self._rom("psx/FF7 (Disc 1).chd")
        self._rom("psx/FF7 (Disc 2).chd")
        self._rom("psx/Crash Bandicoot (USA).chd")
        nomes = sorted(j.nome for j in sistemas.jogos(self.dados))
        self.assertEqual(nomes, ["Crash Bandicoot", "FF7"])

    def test_pronto_depende_do_flatpak_e_do_core(self):
        self._rom("snes/Jogo.sfc")
        (jogo,) = sistemas.jogos(self.dados)
        self.assertFalse(jogo.instalado)
        self.assertEqual(jogo.acoes, ["instalar"])
        (self.home / ".local/share/flatpak/app/org.libretro.RetroArch/current").mkdir(parents=True)
        (jogo,) = sistemas.jogos(self.dados)
        self.assertIn("snes9x", jogo.extra["falta"])
        sistemas.cores_dir().mkdir(parents=True)
        (sistemas.cores_dir() / "snes9x_libretro.so").touch()
        (jogo,) = sistemas.jogos(self.dados)
        self.assertTrue(jogo.instalado)
        self.assertEqual(jogo.acoes, ["jogar"])

    def test_comando_do_retroarch_guarda_save_ao_lado_da_rom(self):
        rom = self._rom("snes/Jogo [b1].sfc")
        (jogo,) = sistemas.jogos(self.dados)
        argv = sistemas.comando(jogo, self.dados)
        self.assertEqual(argv[:3], ["flatpak", "run", f"--filesystem={self.home / 'AllGames'}"])
        self.assertIn("org.libretro.RetroArch", argv)
        self.assertEqual(argv[-1], str(rom))
        self.assertTrue(argv[argv.index("-L") + 1].endswith("cores/snes9x_libretro.so"))
        cfg = Path(argv[argv.index("--appendconfig") + 1]).read_text()
        self.assertIn('savefiles_in_content_dir = "true"', cfg)
        # Clique e joga como no R36S: sair salva, abrir continua, Select+Start sai
        self.assertIn('savestate_auto_save = "true"', cfg)
        self.assertIn('savestate_auto_load = "true"', cfg)
        self.assertIn('input_quit_gamepad_combo = "4"', cfg)
        self.assertIn(str(self.roms / "bios"), cfg)
        # o save com [b1] no nome é achado (o colchete não vira curinga)
        rom.with_suffix(".srm").write_text("save")
        self.assertEqual([p.name for p in saves.arquivos(jogo)], ["Jogo [b1].srm"])

    def test_switch_usa_o_appimage_e_o_comando_do_ryujinx(self):
        self._rom("switch/Jogo.nsp")
        (jogo,) = sistemas.jogos(self.dados)
        self.assertFalse(jogo.instalado)
        pasta = self.home / "AllGames/emuladores/switch"
        pasta.mkdir(parents=True)
        (pasta / "Eden-Linux.AppImage").touch()
        (jogo,) = sistemas.jogos(self.dados)
        self.assertEqual(sistemas.comando(jogo, self.dados)[1:3], ["-f", "-g"])
        (pasta / "Eden-Linux.AppImage").unlink()
        (pasta / "ryujinx-1.3.AppImage").touch()
        self.assertEqual(sistemas.comando(jogo, self.dados)[1], "--fullscreen")

    def test_switch_recebe_chaves_e_firmware_da_pasta_bios(self):
        self._rom("bios/switch/prod.keys", "chaves")
        self._rom("bios/switch/firmware/abc.nca", "fw")
        self._rom("switch/Jogo.nsp")
        (self.home / "AllGames/emuladores/switch").mkdir(parents=True)
        (self.home / "AllGames/emuladores/switch/Eden-Linux.AppImage").touch()
        (jogo,) = sistemas.jogos(self.dados)
        sistemas.comando(jogo, self.dados)
        eden = self.home / ".local/share/eden"
        self.assertEqual((eden / "keys/prod.keys").read_text(), "chaves")
        self.assertTrue((eden / "nand/system/Contents/registered/abc.nca").exists())

    def test_xemu_configurado_com_os_arquivos_do_xbox(self):
        self._rom("bios/xbox/mcpx_1.0.bin")
        self._rom("bios/xbox/Complex_4627.bin")
        self._rom("bios/xbox/xbox_hdd.qcow2")
        config = sistemas.configurar_xemu()
        texto = config.read_text()
        self.assertIn(f'bootrom_path = "{self.roms}/bios/xbox/mcpx_1.0.bin"', texto)
        self.assertIn(f'flashrom_path = "{self.roms}/bios/xbox/Complex_4627.bin"', texto)
        self.assertIn(f'hdd_path = "{self.roms}/bios/xbox/xbox_hdd.qcow2"', texto)
        self.assertIn("show_welcome = false", texto)
        # mantém o que já estava configurado no xemu
        config.write_text(texto + '\n[input.bindings]\nport1 = "pad"\n')
        self.assertIn('port1 = "pad"', sistemas.configurar_xemu().read_text())

    def test_preparar_pastas(self):
        self._rom("megadrive/Jogo.md")
        sistemas.preparar_pastas(self.dados)
        self.assertTrue((self.roms / "psx/LEIA-ME.txt").exists())
        self.assertIn("scph5501.bin", (self.roms / "psx/LEIA-ME.txt").read_text())
        self.assertFalse((self.roms / "genesis").exists(), "já existe a pasta megadrive")
        self.assertTrue((self.roms / "bios").is_dir())
        self.assertTrue((self.home / "AllGames/emuladores/switch").is_dir())

    def test_eden_e_atualizado_mas_outro_emulador_e_respeitado(self):
        pasta = self.home / "AllGames/emuladores/switch"
        with mock.patch.object(sistemas, "_baixar_eden") as baixar:
            sistemas.instalar(["switch"], self.dados)
            self.assertEqual(baixar.call_count, 1)
            pasta.mkdir(parents=True, exist_ok=True)
            (pasta / "Eden-Linux-v0.1.AppImage").touch()
            sistemas.instalar(["switch"], self.dados)
            self.assertEqual(baixar.call_count, 2)
            (pasta / "Eden-Linux-v0.1.AppImage").unlink()
            (pasta / "ryujinx-1.3.AppImage").touch()
            avisos = sistemas.instalar(["switch"], self.dados)
            self.assertEqual(baixar.call_count, 2)
        self.assertTrue(any("prod.keys" in a for a in avisos))

    def test_instalar_alvo_desconhecido(self):
        with self.assertRaisesRegex(ValueError, "não conheço"):
            sistemas.instalar(["playstation9"], self.dados)


if __name__ == "__main__":
    unittest.main()
