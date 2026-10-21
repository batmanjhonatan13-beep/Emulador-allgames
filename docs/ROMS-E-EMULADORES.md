# ROMs e emuladores (como no R36S/ArkOS)

Funciona igual ao ArkOS do R36S: **uma pasta por console**, e toda ROM colocada lá aparece
sozinha no portal, com capa. A diferença é que o jogo roda no PC e você joga pelo celular.

```
~/AllGames/roms/
├── bios/          ← BIOS dos seus consoles (igual à pasta bios do ArkOS)
├── snes/          ← Super Mario World (USA).sfc, Chrono Trigger (USA).sfc...
├── psx/           ← Crash Bandicoot (USA).chd, Final Fantasy VII (USA).m3u...
├── ps2/
├── psp/
├── switch/
└── ...
```

## Começando

```bash
allgames roms                    # cria as pastas (nomes do ArkOS) e mostra quantas ROMs há em cada
# copie as ROMs para ~/AllGames/roms/<pasta>
allgames emuladores instalar     # instala os emuladores que as suas ROMs pedem
```

Também dá para instalar pelo celular: no portal, abra um jogo marcado "Falta o emulador" e toque em
**Instalar o emulador**.

### Trazendo tudo do R36S

Os nomes das pastas são os mesmos do ArkOS. Copie a pasta `roms` do cartão de memória do R36S (a
partição `EASYROMS`) para `~/AllGames/roms`, com a `bios` junto. Como no ArkOS, o RetroArch grava
os saves (`.srm`) **ao lado da ROM**, então os saves que você já tinha no R36S vêm junto e continuam
funcionando.

## Consoles e emuladores

| Pasta | Também aceita | Console | Emulador | BIOS em `roms/bios` |
|---|---|---|---|---|
| `nes` | famicom | Nintendo (NES) | RetroArch (fceumm) | — |
| `snes` | sfc | Super Nintendo | RetroArch (snes9x) | — |
| `gb` / `gbc` / `gba` | | Game Boy / Color / Advance | RetroArch (gambatte, mgba) | — |
| `n64` | | Nintendo 64 | RetroArch (mupen64plus_next) | — |
| `nds` | | Nintendo DS | melonDS (tela de baixo no toque) | — (opcional) |
| `gc` / `wii` | gamecube | GameCube / Wii | Dolphin | — |
| `3ds` | | Nintendo 3DS | Azahar | — |
| **`switch`** | | **Nintendo Switch** | **Eden, Citron ou Ryujinx (AppImage)** | prod.keys e firmware do seu Switch |
| **`psx`** | ps1 | **PlayStation** | RetroArch (Beetle PSX HW) | scph5501.bin (EUA), scph5500.bin, scph5502.bin |
| **`ps2`** | | **PlayStation 2** | PCSX2 | BIOS do seu PS2 |
| **`psp`** | | **PSP** | PPSSPP | — |
| **`xbox`** | | **Xbox** | xemu | mcpx_1.0.bin, BIOS (flash) e HD virtual do Xbox |
| `xbox360` | | Xbox 360 | Xenia Canary (experimental no Linux) | — |
| `genesis` | megadrive, md | Mega Drive | RetroArch (Genesis Plus GX) | — |
| `mastersystem` / `gamegear` | sms / gg | Master System / Game Gear | RetroArch (Genesis Plus GX) | — |
| `segacd` | megacd | Sega CD | RetroArch (Genesis Plus GX) | bios_CD_U.bin, bios_CD_E.bin, bios_CD_J.bin |
| `sega32x` | 32x | Sega 32X | RetroArch (PicoDrive) | — |
| `saturn` | | Sega Saturn | RetroArch (Beetle Saturn) | sega_101.bin, mpr-17933.bin |
| `dreamcast` | dc | Dreamcast | RetroArch (Flycast) | — (opcional) |
| `pcengine` / `pcenginecd` | pce / pcecd | PC Engine / CD | RetroArch (Beetle PCE Fast) | syscard3.pce (CD) |
| `neogeo` | | Neo Geo | RetroArch (FBNeo) | neogeo.zip |
| `arcade` | fbneo, mame, cps1/2/3 | Arcade | RetroArch (FBNeo) | — |
| `atari2600` / `atari7800` / `atarilynx` | lynx | Atari | RetroArch (Stella, ProSystem, Handy) | lynxboot.img (Lynx) |
| `ngp` / `ngpc` | | Neo Geo Pocket / Color | RetroArch (Beetle NGP) | — |
| `wonderswan` / `wonderswancolor` | ws / wsc | WonderSwan / Color | RetroArch (Beetle WonderSwan) | — |
| `msx` | msx2 | MSX | RetroArch (blueMSX) | — |
| `virtualboy` | | Virtual Boy | RetroArch (Beetle VB) | — |
| `dos` | pc | DOS | RetroArch (DOSBox Pure) | — |

Cada pasta recebe um `LEIA-ME.txt` com as extensões aceitas e a BIOS necessária. A lista completa,
com as extensões, está em `catalogo/sistemas.toml`.

### Jogos com mais de um disco (PS1, Sega CD, Saturn...)

Crie uma playlist `.m3u` com um disco por linha:

```
Final Fantasy VII (USA) (Disc 1).chd
Final Fantasy VII (USA) (Disc 2).chd
Final Fantasy VII (USA) (Disc 3).chd
```

O portal mostra só a playlist, e a troca de disco é feita no menu do RetroArch.

## Os consoles principais

- **PlayStation:** precisa da BIOS do seu PS1 em `roms/bios` (`scph5501.bin` para jogos
  americanos). Prefira `.chd` (um arquivo por disco, comprimido) ou `.cue` + `.bin`.
- **PlayStation 2:** na primeira vez, o PCSX2 abre o assistente e pede a BIOS: aponte para
  `~/AllGames/roms/bios`. Depois disso o jogo abre direto em tela cheia.
- **PSP:** não precisa de BIOS. `.iso` ou `.cso`.
- **Xbox (original):** o xemu precisa de três arquivos do seu Xbox (boot ROM MCPX, BIOS e o HD
  virtual). Configure uma vez no xemu (Máquina → Sistema) apontando para `roms/bios/xbox`. Os
  jogos precisam estar no formato **XISO** (`.iso` convertido com o `extract-xiso`).
- **Nintendo Switch:** os principais emuladores (yuzu e Ryujinx) foram encerrados, e as
  continuações (Eden, Citron, Ryujinx da comunidade) mudam de endereço com frequência. Por isso o
  AllGames não baixa um sozinho. Baixe o **AppImage** do emulador no site oficial dele, coloque em
  `~/AllGames/emuladores/switch/` e configure nele as **chaves (`prod.keys`) e o firmware tirados
  do seu Switch**. Jogos `.nsp` ou `.xci` em `roms/switch`. Se o nome do AppImage tiver "ryujinx",
  o AllGames usa os parâmetros do Ryujinx; senão, os do Eden/Citron (`-f -g`).
- **Xbox 360:** o Xenia Canary para Linux ainda é experimental. Muitos jogos não abrem, e os de
  Xbox Live Arcade costumam ir melhor. Coloque o AppImage em `~/AllGames/emuladores/xenia/`.

## Saves

- **RetroArch** (consoles retrô e PS1): ao lado da ROM, como no ArkOS
  (`roms/snes/Super Mario World (USA).srm` e os save states `.state1`...).
- **melonDS:** `.sav` ao lado da ROM.
- **PCSX2, PPSSPP, Dolphin, Azahar:** nas pastas de cada emulador. O catálogo sabe onde ficam, e as
  cópias de segurança automáticas (antes de cada partida) incluem esses arquivos.
- **xemu:** dentro do HD virtual (`xbox_hdd.qcow2`); copie esse arquivo para guardar.

`allgames saves` lista os saves dos jogos do catálogo. Para ROMs, as cópias ficam em
`~/AllGames/backups/rom/<pasta>/<arquivo da ROM>/`.

## Capas

As capas vêm do acervo libretro-thumbnails pelo **nome do arquivo**. ROMs com nomes no padrão
No-Intro/Redump (o que os sites de dump usam, como `Super Mario World (USA).sfc`) ganham capa
sozinhas. Para escolher a capa de uma ROM, coloque uma imagem PNG **com o mesmo nome dela, na
mesma pasta** (`roms/arcade/mslug.png` ao lado de `mslug.zip`). Sem capa, o portal mostra as
iniciais do jogo. Arcade e Neo Geo usam nomes curtos (`mslug.zip`), então precisam disso.

## Mudando o emulador de um console

Tudo fica em `catalogo/sistemas.toml`. Por exemplo, para trocar o core do Super Nintendo pelo
bsnes, mude `core = "snes9x"` para `core = "bsnes"` e rode `allgames emuladores instalar snes`.
Para um emulador novo, crie um `[emulador.<nome>]` com `flatpak` (ou `appimage`) e `comando`.
