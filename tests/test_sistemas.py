import os
import re
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

    def test_copias_repetidas_somem_da_lista(self):
        self._rom("gb/Tetris (World).zip", "tetris")
        self._rom("gb/gb/Tetris (World) - Copy.zip", "tetris")
        self._rom("gb/gb/Tetris (World).zip", "tetris")  # o mesmo arquivo em outra pasta
        for i in range(3):
            self._rom(f"gb/gb/Super Breakout (USA) - Copy ({i}) - Copy - Copy.zip", "breakout")
        # Mesmo nome, jogo diferente (o "Monopoly" de GBC dentro da pasta de GBA): fica.
        self._rom("gb/Monopoly (USA).zip", "monopoly de gb")
        self._rom("gb/gbc/Monopoly (USA).zip", "monopoly de gbc, outro tamanho")
        jogos = sistemas.jogos(self.dados)
        self.assertEqual(sorted(j.nome for j in jogos), ["Monopoly", "Monopoly", "Super Breakout", "Tetris"])
        tetris = next(j for j in jogos if j.nome == "Tetris")
        self.assertEqual(tetris.extra["rom"], str(self.roms / "gb/Tetris (World).zip"))
        breakout = next(j for j in sistemas.jogos(self.dados) if j.nome == "Super Breakout")
        self.assertTrue(breakout.capa.endswith("/Super Breakout (USA)"))

    def test_nome_e_capa_do_emulationstation_do_arkos(self):
        self._rom("neogeo/neogeo.zip")  # a BIOS não aparece como jogo
        self._rom("neogeo/sonicwi3.zip")
        self._rom("neogeo/kof97.zip")
        imagem = self.roms / "neogeo/downloaded_images/kof97-image.png"
        imagem.parent.mkdir(parents=True)
        imagem.write_bytes(b"png")
        (self.roms / "neogeo/boxart").mkdir()
        (self.roms / "neogeo/boxart/sw3.png").write_bytes(b"png")
        (self.roms / "neogeo/gamelist.xml").write_text(
            "<gameList><game><path>./sonicwi3.zip</path><name>Aero Fighters 3 (set 1)</name>"
            "<image>./boxart/sw3.png</image></game></gameList>"
        )
        jogos = {j.extra["rom"].rsplit("/", 1)[1]: j for j in sistemas.jogos(self.dados)}
        self.assertNotIn("neogeo.zip", jogos)
        self.assertEqual(jogos["sonicwi3.zip"].nome, "Aero Fighters 3")
        self.assertEqual(jogos["sonicwi3.zip"].extra["capa_local"], str(self.roms / "neogeo/boxart/sw3.png"))
        # Sem entrada no gamelist: a imagem do scraper com o nome da ROM.
        self.assertEqual(jogos["kof97.zip"].extra["capa_local"], str(imagem))

    def test_perfil_do_controle_do_moonlight_e_os_que_vem_com_o_retroarch(self):
        estoque = self.home / ".local/share/flatpak" / sistemas._PERFIS_DO_FLATPAK / "udev"
        estoque.mkdir(parents=True)
        (estoque / "Microsoft X-Box 360 pad.cfg").write_text('input_device = "Microsoft X-Box 360 pad"\n')
        self._rom("psx/Crash.pbp")
        (jogo,) = sistemas.jogos(self.dados)
        argv = sistemas.comando(jogo, self.dados)
        cfg = Path(argv[argv.index("--appendconfig") + 1]).read_text()
        pasta = Path(re.search(r'joypad_autoconfig_dir = "([^"]+)"', cfg).group(1)) / "udev"
        self.assertTrue((pasta / "Microsoft X-Box 360 pad.cfg").exists())
        perfil = (pasta / "Sunshine X-Box 360 (Moonlight).cfg").read_text()
        self.assertIn('input_device = "Sunshine (libvirtualhid) X-Box 360 Controller"', perfil)
        # Quadrado (Y do RetroPad) é o X do controle, que o kernel numera como 3; Start é o 11.
        self.assertIn('input_y_btn = "3"', perfil)
        self.assertIn('input_start_btn = "11"', perfil)

    def test_retroarch_usa_vulkan_e_n64_no_parallel_sem_apagar_o_que_voce_mudou(self):
        self._rom("n64/Jogo.z64")
        (jogo,) = sistemas.jogos(self.dados)
        argv = sistemas.comando(jogo, self.dados)
        cfg = Path(argv[argv.index("--appendconfig") + 1]).read_text()
        self.assertIn('video_driver = "vulkan"', cfg)
        opcoes = Path(re.search(r'core_options_path = "([^"]+)"', cfg).group(1))
        self.assertIn('mupen64plus-rdp-plugin = "parallel"', opcoes.read_text())
        # Você trocou pelo menu do RetroArch: o AllGames não desfaz.
        opcoes.write_text('mupen64plus-rdp-plugin = "gliden64"\nmupen64plus-rsp-plugin = "hle"\n')
        sistemas.comando(jogo, self.dados)
        self.assertEqual(opcoes.read_text(), 'mupen64plus-rdp-plugin = "gliden64"\nmupen64plus-rsp-plugin = "hle"\n')

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
