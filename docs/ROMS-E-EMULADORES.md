# ROMs e emuladores (como no R36S/ArkOS)

Funciona igual ao ArkOS do R36S: **uma pasta por console**, e toda ROM colocada lá aparece
sozinha no portal, com capa. A diferença é que o jogo roda no PC e você joga pelo celular.

No Docker, essa pasta é a `ROMS` do `docker/.env` (por padrão a mesma `~/AllGames/roms`). Veja
[DOCKER.md](DOCKER.md).

## Clique e joga

Como no R36S, não tem emulador para configurar:

- **Os emuladores se instalam sozinhos.** No Docker isso acontece na primeira vez que o container
  liga; sem Docker, rode `allgames emuladores instalar --todos` uma vez (ou toque em **Instalar o
  emulador** no portal).
- **Quase tudo roda no RetroArch**, já configurado: tela cheia, controle detectado sozinho, BIOS
  lida de `roms/bios`.
- **Sair salva.** Segure **Select + Start** para sair: o RetroArch grava o estado do jogo, e na
  próxima vez ele **continua de onde parou**. O save normal do jogo (`.srm`) também é gravado a
  cada 10 segundos, então nada se perde se a conexão cair.
- **L3 + R3** (apertar os dois direcionais) abre o menu do RetroArch, se precisar.
- Nos emuladores avulsos (Switch, 3DS, Xbox e os ports do PortMaster) segurar **Select + Start**
  por um segundo também fecha o jogo. Neles, o progresso é o save do próprio jogo: salve no jogo
  antes de sair.

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
allgames emuladores instalar     # instala os emuladores que as suas ROMs pedem (--todos: todos)
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
| `nds` | | Nintendo DS | RetroArch (melonDS DS) | — (opcional) |
| `gc` / `wii` | gamecube | GameCube / Wii | RetroArch (Dolphin) | — |
| `3ds` | | Nintendo 3DS | Azahar | — |
| **`switch`** | | **Nintendo Switch** | **Eden (baixado sozinho)** | `switch/`: prod.keys, title.keys e firmware do seu Switch |
| **`psx`** | ps1 | **PlayStation** | RetroArch (Beetle PSX HW) | scph5501.bin (EUA), scph5500.bin, scph5502.bin |
| **`ps2`** | | **PlayStation 2** | RetroArch (LRPS2, baseado no PCSX2) | `pcsx2/bios/` com a BIOS do seu PS2 |
| **`psp`** | | **PSP** | RetroArch (PPSSPP) | — |
| **`xbox`** | | **Xbox** | xemu | `xbox/`: mcpx_1.0.bin, BIOS (flash) e HD virtual do Xbox |
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
- **PlayStation 2:** coloque a BIOS do seu PS2 em `roms/bios/pcsx2/bios/` (por exemplo
  `SCPH-70012.bin`). O jogo abre direto em tela cheia, com o mesmo auto-save dos outros consoles.
  Se algum jogo for melhor no PCSX2 completo, troque `emulador = "pcsx2"` no sistema `ps2` do
  `catalogo/sistemas.toml`.
- **PSP:** não precisa de BIOS. `.iso` ou `.cso`. Os arquivos de apoio do PPSSPP (fontes, etc.)
  são baixados sozinhos para `roms/bios/PPSSPP`.
- **GameCube e Wii:** os arquivos de apoio do Dolphin também são baixados sozinhos.
- **Xbox (original):** coloque em `roms/bios/xbox/` os três arquivos do seu Xbox: o boot ROM
  (`mcpx_1.0.bin`), a BIOS (flash, por exemplo `Complex_4627.bin`) e o HD virtual
  (`xbox_hdd.qcow2`). O AllGames configura o xemu sozinho antes de abrir o jogo. Os jogos precisam
  estar no formato **XISO** (`.iso` convertido com o `extract-xiso`).
- **Nintendo Switch:** o AllGames usa o **[Eden](https://eden-emu.dev/downloads/)** e **baixa a
  versão mais nova sozinho** (AppImage para Linux) em `~/AllGames/emuladores/switch/`. Coloque em
  `roms/bios/switch/` as **chaves (`prod.keys` e `title.keys`) e a pasta `firmware` tiradas do seu
  Switch**: a cada partida o AllGames instala o que estiver lá no Eden. Jogos `.nsp` ou `.xci` em
  `roms/switch`. Na primeira vez, confira o controle em **Emulação → Configurar → Controles**
  (escolha o "Xbox 360 Controller" do Sunshine). Prefere outro emulador? Coloque o AppImage dele
  na mesma pasta e apague o do Eden; se o nome tiver "ryujinx", o AllGames usa os parâmetros do
  Ryujinx.
- **Xbox 360:** o Xenia Canary para Linux ainda é experimental. Muitos jogos não abrem, e os de
  Xbox Live Arcade costumam ir melhor. Coloque o AppImage em `~/AllGames/emuladores/xenia/`.

## Saves

- **RetroArch** (consoles retrô, PS1, PS2, PSP, DS, GameCube e Wii): ao lado da ROM, como no
  ArkOS (`roms/snes/Super Mario World (USA).srm`, o estado de quando você saiu em `.state.auto` e
  os save states manuais `.state1`...).
- **Eden, Azahar:** nas pastas de cada emulador. O catálogo sabe onde ficam, e as cópias de
  segurança automáticas (antes de cada partida) incluem esses arquivos.
- **xemu:** dentro do HD virtual (`roms/bios/xbox/xbox_hdd.qcow2`); copie esse arquivo para
  guardar.
- **PortMaster:** na pasta de cada port (veja [PORTMASTER.md](PORTMASTER.md)).

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
