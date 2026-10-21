"""O AllGames no Windows, simulado no Linux (o código só olha sys.platform e os caminhos)."""

import io
import json
import os
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from allgames import biblioteca, portal, sistemas, sunshine, supervisor, windows

# Nomes reais dos zips nas páginas de versões (outubro de 2026).
PAGINAS = {
    "switch": [
        "Eden-Linux-v0.2.1-amd64-clang-pgo.AppImage",
        "Eden-Windows-v0.2.1-amd64-clang-pgo.zip",
        "Eden-Windows-v0.2.1-amd64-msvc-standard.zip",
        "Eden-Windows-v0.2.1-arm64-clang-pgo.zip",
    ],
    "xemu": ["xemu-0.8.138-dbg-windows-x86_64.zip", "xemu-win-x86_64-release.zip", "xemu-0.8.138-x86_64.AppImage"],
    "azahar": [
        "azahar-libretro-windows-x86_64-2126.2.zip",
        "azahar-windows-msvc-2126.2-installer.exe",
        "azahar-windows-msvc-2126.2.zip",
    ],
    "xenia": ["xenia_canary_linux.tar.gz", "xenia_canary_windows_.zip"],
}
ESPERADO = {
    "switch": "Eden-Windows-v0.2.1-amd64-clang-pgo.zip",
    "xemu": "xemu-win-x86_64-release.zip",
    "azahar": "azahar-windows-msvc-2126.2.zip",
    "xenia": "xenia_canary_windows_.zip",
}


class ZipsDosEmuladores(unittest.TestCase):
    def test_escolhe_o_zip_para_windows_de_cada_emulador(self):
        emuladores, _ = sistemas.carregar()
        for chave, nomes in PAGINAS.items():
            assets = [{"name": n} for n in nomes]
            escolhido = windows.escolher_arquivo(assets, emuladores[chave].windows["arquivos"])
            self.assertEqual(escolhido["name"], ESPERADO[chave], chave)

    def test_baixa_e_extrai_achando_o_exe_numa_subpasta(self):
        pacote = io.BytesIO()
        with zipfile.ZipFile(pacote, "w") as z:
            z.writestr("azahar-windows-msvc-2126.2/azahar.exe", b"MZ")
        pagina = json.dumps({"assets": [{"name": "azahar-windows-msvc-2126.2.zip", "browser_download_url": "u"}]})
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp) / "azahar"
            with mock.patch.object(windows, "_baixar", side_effect=[pagina.encode(), pacote.getvalue()]):
                windows.baixar_zip(["api"], [r"(?i)windows.*msvc.*\.zip$"], pasta)
            self.assertEqual(windows.exe_baixado(pasta, "Azahar.exe").name, "azahar.exe")


class SistemasNoWindows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        os.environ["ALLGAMES_HOME"] = str(self.raiz / "AllGames")
        self.retroarch = self.raiz / "RetroArch-Win64/retroarch.exe"
        self.retroarch.parent.mkdir(parents=True)
        self.retroarch.write_bytes(b"MZ")
        for alvo in (
            mock.patch.object(sistemas, "WINDOWS", True),
            mock.patch.object(windows, "ATIVO", True),
            mock.patch.object(windows, "retroarch", return_value=self.retroarch),
            mock.patch.object(windows, "appdata", return_value=self.raiz / "Roaming"),
        ):
            alvo.start()
            self.addCleanup(alvo.stop)
        self.dados = sistemas.carregar()

    def tearDown(self):
        os.environ.pop("ALLGAMES_HOME")
        self.tmp.cleanup()

    def _rom(self, caminho):
        rom = sistemas.roms_dir() / caminho
        rom.parent.mkdir(parents=True, exist_ok=True)
        rom.write_bytes(b"rom")
        return rom

    def test_retroarch_com_core_dll_sem_perfil_de_controle_do_linux(self):
        rom = self._rom("snes/Zoop (USA).zip")
        (jogo,) = sistemas.jogos(self.dados)
        self.assertEqual(
            sistemas.pronto(self.dados[0]["retroarch"], self.dados[1][1]), (False, "instale o core snes9x do RetroArch")
        )
        core = sistemas.cores_dir() / "snes9x_libretro.dll"
        core.parent.mkdir(parents=True)
        core.write_bytes(b"MZ")
        argv = sistemas.comando(jogo, self.dados)
        self.assertEqual(argv[0], str(self.retroarch))
        self.assertEqual(argv[argv.index("-L") + 1], str(core))
        self.assertEqual(argv[-1], str(rom))
        cfg = Path(argv[argv.index("--appendconfig") + 1]).read_text()
        self.assertNotIn("joypad_autoconfig_dir", cfg)
        self.assertIn('input_quit_gamepad_combo = "4"', cfg)

    def test_baixa_o_core_da_versao_windows(self):
        pacote = io.BytesIO()
        with zipfile.ZipFile(pacote, "w") as z:
            z.writestr("snes9x_libretro.dll", b"MZ")
        with mock.patch.object(sistemas, "_baixar", return_value=pacote.getvalue()) as baixar:
            sistemas._baixar_core("snes9x")
        self.assertIn("/windows/x86_64/", baixar.call_args.args[0])
        self.assertTrue((sistemas.cores_dir() / "snes9x_libretro.dll").exists())

    def test_eden_baixado_e_chaves_do_switch_no_appdata(self):
        self._rom("switch/Zelda.nsp")
        (jogo,) = sistemas.jogos(self.dados)
        self.assertFalse(jogo.situacao)
        eden = sistemas.emuladores_dir() / "switch/Eden/eden.exe"
        eden.parent.mkdir(parents=True)
        eden.write_bytes(b"MZ")
        chaves = sistemas.bios_dir() / "switch/prod.keys"
        chaves.parent.mkdir(parents=True)
        chaves.write_text("chaves")
        (jogo,) = sistemas.jogos(self.dados)
        self.assertTrue(jogo.situacao)
        argv = sistemas.comando(jogo, self.dados)
        self.assertEqual(argv[:3], [str(eden), "-f", "-g"])
        self.assertEqual((self.raiz / "Roaming/eden/keys/prod.keys").read_text(), "chaves")

    def test_emulador_sem_versao_windows_avisa(self):
        emuladores, _ = self.dados
        self.assertEqual(sistemas.pronto(emuladores["melonds"]), (False, "o melonDS ainda não roda no Windows"))

    def test_biblioteca_sem_jogos_que_so_existem_no_linux(self):
        self._rom("gba/Pokemon.gba")
        with mock.patch.object(biblioteca.lojas, "jogos", return_value=[]):
            origens = {j.origem for j in biblioteca.todos()}
        self.assertEqual(origens, {"rom"})


class PortalESunshineNoWindows(unittest.TestCase):
    def test_portal_abre_no_edge_em_tela_cheia(self):
        edge = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
        with (
            mock.patch.object(windows, "ATIVO", True),
            mock.patch.object(windows, "edge", return_value=edge),
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.dict(os.environ, {"ALLGAMES_HOME": tmp}),
        ):
            os.environ.pop("ALLGAMES_NAVEGADOR", None)
            argv = portal.comando_navegador("http://127.0.0.1:47800/")
        self.assertEqual(argv[0], str(edge))
        self.assertIn("--kiosk", argv)
        self.assertIn("http://127.0.0.1:47800/", argv)

    def test_app_do_sunshine_chama_o_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            pythonw = Path(tmp) / "pythonw.exe"
            pythonw.write_bytes(b"MZ")
            with (
                mock.patch.object(windows, "ATIVO", True),
                mock.patch.object(sys, "executable", str(Path(tmp) / "python.exe")),
            ):
                app = sunshine.app_do_portal()
        self.assertTrue(app["cmd"].startswith(f'"{pythonw}" -X utf8 "'))
        self.assertTrue(app["cmd"].endswith('allgames" portal --kiosk'))
        self.assertTrue(
            sunshine.eh_nosso({"cmd": r'"C:\Py\pythonw.exe" "C:\Users\a\AllGames\app\bin\allgames" portal'})
        )


class XInputDeMentira:
    """Imita o XInputGetState: o controle 0 com os botões pedidos, os outros desconectados."""

    def __init__(self, botoes):
        self.botoes = botoes

    def XInputGetState(self, indice, ponteiro):  # noqa: N802 - nome da função do Windows
        if indice:
            return 1167  # ERROR_DEVICE_NOT_CONNECTED
        estado = ponteiro._obj  # o ctypes.byref guarda a estrutura aqui
        estado.Gamepad.wButtons = self.botoes
        return 0


class ControlesNoWindows(unittest.TestCase):
    def test_select_start_pelo_xinput(self):
        apertado = supervisor.ControlesXInput(XInputDeMentira(0x0020 | 0x0010))
        apertado.ler(0)
        self.assertTrue(apertado.combo_apertado())
        so_start = supervisor.ControlesXInput(XInputDeMentira(0x0010))
        so_start.ler(0)
        self.assertFalse(so_start.combo_apertado())

    def test_sem_xinput_nao_quebra(self):
        controles = supervisor.ControlesXInput(dll=False)
        controles.ler(0)
        self.assertFalse(controles.combo_apertado())


class CatalogoDoWindows(unittest.TestCase):
    def test_padroes_validos(self):
        emuladores, _ = sistemas.carregar()
        for emulador in emuladores.values():
            for padrao in emulador.windows.get("arquivos", []):
                re.compile(padrao)


if __name__ == "__main__":
    unittest.main()
