import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from allgames import lojas

MANIFESTO = '"AppState"\n{\n\t"appid"\t\t"%s"\n\t"name"\t\t"%s"\n\t"StateFlags"\t\t"%s"\n}\n'


class Vdf(unittest.TestCase):
    def test_le_blocos_aninhados(self):
        texto = (
            '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"/home/a/Steam"\n'
            '\t\t"apps"\n\t\t{\n\t\t\t"10"\t"1"\n\t\t}\n\t}\n}'
        )
        dados = lojas._vdf(texto)
        self.assertEqual(dados["libraryfolders"]["0"]["path"], "/home/a/Steam")
        self.assertEqual(dados["libraryfolders"]["0"]["apps"], {"10": "1"})

    def test_escreve_e_le_de_volta(self):
        dados = {"a": {"b": 'tem "aspas" e \\barra', "c": {}, "d": {"1": "2"}}}
        self.assertEqual(
            lojas._vdf(lojas._vdf_texto(dados)), {"a": {"b": 'tem "aspas" e \\barra', "c": {}, "d": {"1": "2"}}}
        )


class Lojas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.patch = mock.patch("pathlib.Path.home", return_value=self.home)
        self.patch.start()
        os.environ.pop("ALLGAMES_HOME", None)

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_registra_os_jogos_da_steam_do_pc_sem_duplicar(self):
        principal = self.home / ".local/share/Steam/steamapps"
        principal.mkdir(parents=True)
        vdf = (
            f'"libraryfolders"\n{{\n\t"0"\n\t{{\n\t\t"path"\t\t"{principal.parent}"\n\t\t"apps"\n\t\t{{\n\t\t}}\n\t}}\n'
            '\t"1"\n\t{\n\t\t"path"\t\t"/mnt/games/GameLibrary/Steam"\n\t}\n}\n'
        )
        (principal / "libraryfolders.vdf").write_text(vdf)
        do_pc = self.home / "Jogos/SteamPC"
        (do_pc / "steamapps").mkdir(parents=True)
        (do_pc / "steamapps/appmanifest_1174180.acf").write_text(MANIFESTO % ("1174180", "Red Dead Redemption 2", "4"))
        self.assertTrue(lojas.registrar_biblioteca_steam(do_pc))
        self.assertFalse(lojas.registrar_biblioteca_steam(do_pc), "já registrada: não muda nada")
        pastas = lojas._vdf((principal / "libraryfolders.vdf").read_text())["libraryfolders"]
        self.assertEqual(list(pastas), ["0", "1", "2"])
        self.assertEqual(pastas["2"]["path"], str(do_pc))
        self.assertEqual(pastas["2"]["apps"], {"1174180": "0"})
        self.assertEqual(pastas["1"]["path"], "/mnt/games/GameLibrary/Steam")
        self.assertTrue((do_pc / "libraryfolder.vdf").exists())
        self.assertEqual(lojas.steam_instalados(), {"1174180": "Red Dead Redemption 2"})

    def _steam(self, biblioteca_extra=True):
        raiz = self.home / ".local/share/Steam"
        (raiz / "steamapps").mkdir(parents=True)
        extra = self.home / "HD/SteamLibrary"
        (extra / "steamapps").mkdir(parents=True)
        (raiz / "steamapps/libraryfolders.vdf").write_text(
            f'"libraryfolders"\n{{\n"0"\n{{\n"path" "{raiz}"\n}}\n"1"\n{{\n"path" "{extra}"\n}}\n}}'
        )
        (raiz / "steamapps/appmanifest_254700.acf").write_text(MANIFESTO % ("254700", "Resident Evil 4", "4"))
        (raiz / "steamapps/appmanifest_1493710.acf").write_text(MANIFESTO % ("1493710", "Proton Experimental", "4"))
        (raiz / "steamapps/appmanifest_10.acf").write_text(MANIFESTO % ("10", "Baixando", "1026"))
        (extra / "steamapps/appmanifest_1245620.acf").write_text(MANIFESTO % ("1245620", "ELDEN RING", "4"))

    def test_steam_fica_fora_do_portal_a_nao_ser_que_voce_peca(self):
        self._steam()
        self.assertEqual([j for j in lojas.jogos() if j.origem == "steam"], [])
        config = self.home / "AllGames/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text("[steam]\nmostrar_no_portal = true\n")
        self.assertIn("steam:254700", {j.id for j in lojas.jogos()})

    def test_steam_instalados_em_todas_as_bibliotecas(self):
        self._steam()
        # Proton é ferramenta e o 10 ainda está baixando (StateFlags sem o bit 4).
        self.assertEqual(lojas.steam_instalados(), {"254700": "Resident Evil 4", "1245620": "ELDEN RING"})

    def test_steam_biblioteca_com_chave(self):
        self._steam()
        (self.home / "AllGames").mkdir()
        (self.home / "AllGames/config.toml").write_text('[steam]\nchave_api = "abc"\nsteamid = "765"\n')
        resposta = json.dumps({"response": {"games": [{"appid": 220, "name": "Half-Life 2"}, {"appid": 254700}]}})
        with mock.patch("urllib.request.urlopen", mock.mock_open(read_data=resposta.encode())):
            jogos = {j.id: j for j in lojas.steam_jogos()}
        self.assertFalse(jogos["steam:220"].instalado)
        self.assertEqual(jogos["steam:220"].acoes, ["instalar"])
        self.assertTrue(jogos["steam:254700"].instalado)
        self.assertEqual(jogos["steam:254700"].nome, "Resident Evil 4")
        self.assertIn("library_600x900.jpg", jogos["steam:220"].capa_url)
        # segunda leitura vem do cache, sem rede
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("não devia usar a rede")):
            self.assertIn("steam:220", {j.id for j in lojas.steam_jogos()})

    def test_heroic(self):
        raiz = self.home / ".config/heroic"
        (raiz / "store_cache").mkdir(parents=True)
        (raiz / "legendaryConfig/legendary").mkdir(parents=True)
        (raiz / "store_cache/legendary_library.json").write_text(
            json.dumps(
                {
                    "library": [
                        {
                            "app_name": "Fortnite",
                            "title": "Fortnite",
                            "is_installed": False,
                            "art_square": "http://x/f.jpg",
                        },
                        {"app_name": "abc", "title": "GTA V", "is_installed": False},
                        {"app_name": "Kinglet", "title": "AC Unity", "isUbisoftManaged": True},
                    ]
                }
            )
        )
        (raiz / "legendaryConfig/legendary/installed.json").write_text(
            json.dumps({"abc": {"install_path": "/jogos/GTAV"}})
        )
        (raiz / "store_cache/gog_library.json").write_text(
            json.dumps({"games": [{"app_name": "1", "title": "Witcher 3"}]})
        )
        jogos = {j.id: j for j in lojas.heroic_jogos()}
        self.assertEqual(
            set(jogos),
            {"heroic:legendary:Fortnite", "heroic:legendary:abc", "heroic:legendary:Kinglet", "heroic:gog:1"},
        )
        gta = jogos["heroic:legendary:abc"]
        self.assertTrue(gta.instalado)
        self.assertEqual(gta.extra["pasta"], "/jogos/GTAV")
        self.assertEqual(gta.acoes, ["jogar", "desinstalar"])
        self.assertEqual(jogos["heroic:legendary:Fortnite"].capa_url, "http://x/f.jpg")
        self.assertIn("Ubisoft Connect", jogos["heroic:legendary:Kinglet"].descricao)
        self.assertEqual(jogos["heroic:gog:1"].plataforma, "GOG")
        url = lojas._heroic_url(gta, gui=False)
        self.assertEqual(url, "heroic://launch?appName=abc&runner=legendary&gui=false")

    def test_sem_steam_e_sem_heroic(self):
        self.assertEqual(lojas.jogos(), [])
        jogo = lojas.Jogo("steam:1", "X", "Steam", "pc", origem="steam", extra={"appid": "1"})
        with mock.patch("shutil.which", return_value=None), self.assertRaisesRegex(RuntimeError, "Steam"):
            lojas.acao(jogo, "instalar")

    def test_esperar_processo(self):
        estados = iter(
            [
                [],
                [(1, "reaper SteamLaunch AppId=254700 -- jogo", "/")],
                [(1, "reaper SteamLaunch AppId=254700 -- jogo", "/")],
                [],
            ]
        )
        with mock.patch.object(lojas, "_processos", side_effect=lambda: iter(next(estados))), mock.patch("time.sleep"):
            self.assertTrue(lojas.esperar_processo(lambda c, _: "AppId=254700" in c))

    def test_esperar_processo_que_nunca_aparece(self):
        with mock.patch.object(lojas, "_processos", return_value=iter([])), mock.patch("time.sleep"):
            self.assertFalse(lojas.esperar_processo(lambda c, _: True, aparecer=0))


if __name__ == "__main__":
    unittest.main()
