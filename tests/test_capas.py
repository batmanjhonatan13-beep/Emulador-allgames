import unittest

from allgames.capas import url_libretro


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


if __name__ == "__main__":
    unittest.main()
