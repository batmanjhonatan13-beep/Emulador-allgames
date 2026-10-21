import json
import os
import stat
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from allgames import downloads

MANIFESTO = (
    '"AppState"\n{\n\t"appid"\t\t"%s"\n\t"name"\t\t"%s"\n\t"StateFlags"\t\t"%s"\n'
    '\t"BytesToDownload"\t\t"%s"\n\t"BytesDownloaded"\t\t"%s"\n}\n'
)

# Saída de verdade do legendary (só o que interessa ao AllGames).
LEGENDARY_FALSO = r"""#!/usr/bin/env python3
import sys, time
open(sys.argv[0] + ".args", "w").write(" ".join(sys.argv[1:]))
print("[cli] INFO: Install path: /jogos/Epic/Celeste", flush=True)
print("[cli] INFO: Download size: 1024.00 MiB (Compression savings: 0.0%)", flush=True)
print("[DLManager] INFO: = Progress: 25.00% (10/40), Running for 00:00:10, ETA: 00:01:05", flush=True)
print("[DLManager] INFO:  - Downloaded: 256.00 MiB, Written: 256.00 MiB", flush=True)
print("[DLManager] INFO:  + Download\t- 12.50 MiB/s (raw) / 25.00 MiB/s (decompressed)", flush=True)
time.sleep(30)
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.patch = mock.patch("pathlib.Path.home", return_value=self.home)
        self.patch.start()
        os.environ.pop("ALLGAMES_HOME", None)
        (self.home / "AllGames").mkdir()
        (self.home / "AllGames/config.toml").write_text(f'[epic]\npasta = "{self.home}/Epic"\n')

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()


class Steam(Base):
    def _manifesto(self, appid, nome, flags, total=0, feito=0):
        pasta = self.home / ".local/share/Steam/steamapps"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / f"appmanifest_{appid}.acf").write_text(MANIFESTO % (appid, nome, flags, total, feito))

    def test_estados_dos_downloads(self):
        self._manifesto("1", "Instalado", 4)
        self._manifesto("2", "God of War Ragnarök", 1026, 100, 40)
        self._manifesto("3", "Pausado", 512 | 2, 100, 10)
        self._manifesto("4", "Na fila", 2, 100, 0)
        self._manifesto("5", "Steamworks Common Redistributables", 1026, 100, 0)
        lista = {d["id"]: d for d in downloads.steam_downloads()}
        self.assertEqual(sorted(lista), ["steam:2", "steam:3", "steam:4"])
        self.assertEqual(lista["steam:2"]["estado"], "baixando")
        self.assertEqual((lista["steam:2"]["baixado"], lista["steam:2"]["total"]), (40, 100))
        self.assertEqual(lista["steam:3"]["estado"], "pausado")
        self.assertEqual(lista["steam:4"]["estado"], "na fila")
        self.assertEqual(lista["steam:2"]["acoes"], ["abrir_steam"])

    def test_velocidade_tempo_e_espaco(self):
        self._manifesto("2", "God of War Ragnarök", 1026, 10_000, 1_000)
        fila = downloads.Downloads()
        with mock.patch("time.monotonic", return_value=100.0):
            (item,) = fila.lista()
        self.assertEqual(item["velocidade"], 0)
        self.assertIsNone(item["restante"])
        self._manifesto("2", "God of War Ragnarök", 1026, 10_000, 3_000)
        with mock.patch("time.monotonic", return_value=110.0):
            (item,) = fila.lista()
        self.assertEqual(item["velocidade"], 200)
        self.assertEqual(item["restante"], 35)
        self.assertTrue(item["cabe"])
        self._manifesto("2", "God of War Ragnarök", 1026, 10**18, 3_000)
        (item,) = fila.lista()
        self.assertFalse(item["cabe"], "o jogo não cabe no disco")


class Discos(Base):
    def test_um_item_por_disco(self):
        (self.home / "AllGames/roms").mkdir()
        (disco,) = downloads.discos()  # tudo na mesma pasta temporária
        self.assertEqual(sorted(disco["nomes"]), ["AllGames", "Epic", "ROMs"])
        self.assertGreater(disco["total"], 0)
        self.assertLessEqual(disco["livre"], disco["total"])

    def test_pasta_da_epic(self):
        self.assertEqual(downloads.pasta_epic(), self.home / "Epic")


class Epic(Base):
    def setUp(self):
        super().setUp()
        binarios = self.home / "bin"
        binarios.mkdir()
        self.legendary = binarios / "legendary"
        self.legendary.write_text(LEGENDARY_FALSO)
        self.legendary.chmod(self.legendary.stat().st_mode | stat.S_IEXEC)
        self.path = mock.patch.dict(os.environ, {"PATH": f"{binarios}{os.pathsep}{os.environ['PATH']}"})
        self.path.start()
        self.fila = downloads.Downloads()

    def tearDown(self):
        for download in self.fila.epic.values():
            download.pausar()
        self.path.stop()
        super().tearDown()

    def _esperar(self, condicao):
        limite = time.monotonic() + 10
        while not condicao():
            self.assertLess(time.monotonic(), limite, "o download falso não respondeu")
            time.sleep(0.05)

    def test_progresso_pausa_e_retomada(self):
        download = self.fila.baixar_epic("epic:Salt", "Salt", "Celeste")
        self._esperar(lambda: download.velocidade)
        item = download.como_dict()
        self.assertEqual(item["estado"], "baixando")
        self.assertEqual(item["total"], 1024 * 1024**2)
        self.assertEqual(item["baixado"], 256 * 1024**2)
        self.assertEqual(item["velocidade"], int(12.5 * 1024**2))
        self.assertEqual(item["restante"], 65)
        self.assertEqual(item["pasta"], "/jogos/Epic/Celeste")
        self.assertEqual(item["acoes"], ["pausar"])
        self.assertIn(f"install Salt -y --base-path {self.home / 'Epic'}", Path(f"{self.legendary}.args").read_text())

        self.fila.acao("epic:Salt", "pausar")
        self._esperar(lambda: download.estado == "pausado")
        self._esperar(lambda: json.loads(self.fila.arquivo.read_text())[0]["estado"] == "pausado")
        self.assertEqual(download.como_dict()["acoes"], ["continuar", "cancelar"])

        # Depois de reiniciar o AllGames o download volta pausado, com o progresso.
        de_novo = downloads.Downloads()
        self.assertEqual(de_novo.epic["epic:Salt"].estado, "pausado")
        self.assertEqual(de_novo.epic["epic:Salt"].baixado, 256 * 1024**2)

        self.fila.acao("epic:Salt", "continuar")
        self._esperar(lambda: download.estado == "baixando" and download.velocidade)
        self.fila.acao("epic:Salt", "cancelar")
        self._esperar(lambda: download._processo.poll() is not None and download.estado == "pausado")
        self.assertEqual(self.fila.epic, {})
        self.assertEqual(json.loads(self.fila.arquivo.read_text()), [])

    def test_ao_continuar_a_barra_nao_volta(self):
        download = downloads.DownloadEpic("epic:Salt", "Salt", "Celeste", "pausado", 600 * 1024**2, 1024 * 1024**2)
        download._ler("[cli] INFO: Download size: 424.00 MiB (Compression savings: 0.0%)")
        download._ler("[DLManager] INFO:  - Downloaded: 24.00 MiB, Written: 24.00 MiB")
        self.assertEqual((download.baixado, download.total), (624 * 1024**2, 1024 * 1024**2))
        download._ler("[DLManager] INFO: = Progress: 50.00% (1/2), Running for 00:00:10, ETA: 00:00:10")
        self.assertEqual(download.baixado, 812 * 1024**2)

    def test_acao_desconhecida(self):
        with self.assertRaises(ValueError):
            self.fila.acao("epic:nada", "pausar")


if __name__ == "__main__":
    unittest.main()
