# Pokémon e Resident Evil 4 na lista de descompilações

Este guia mostra o que a lista [SamidyFR/Game-Decompilations](https://github.com/SamidyFR/Game-Decompilations)
tem de Pokémon e de Resident Evil 4 e como cada jogo entrou no AllGames. Situação em outubro de 2026.

## Por que a maioria roda em emulador

Quase todas as descompilações de Pokémon (as do grupo [pret](https://github.com/pret)) são
**"matching"**: o código reconstruído compila para uma ROM **idêntica, byte a byte**, à original.
Elas servem para estudar o jogo e criar ROM hacks, mas o resultado é o próprio cartucho. Para jogar,
basta rodar a sua ROM num emulador. O AllGames confere a ROM com o **mesmo SHA-1** que cada
projeto do pret usa para validar o resultado, por isso o nome do arquivo não importa.

Quando a descompilação ganha um **port nativo** (código reescrito para rodar direto no PC, sem
emulador), o AllGames usa o port. O caso do Pokémon Snap é esse.

## Pokémon

| Jogo da lista | Descompilação | No AllGames | Como roda |
|---|---|---|---|
| Pokémon Red / Blue | [pret/pokered](https://github.com/pret/pokered) | `pokemon-red`, `pokemon-blue` | mGBA |
| Pokémon Yellow | [pret/pokeyellow](https://github.com/pret/pokeyellow) | `pokemon-yellow` | mGBA |
| Pokémon Gold / Silver | [pret/pokegold](https://github.com/pret/pokegold) | `pokemon-gold`, `pokemon-silver` | mGBA |
| Pokémon Crystal | [pret/pokecrystal](https://github.com/pret/pokecrystal) | `pokemon-crystal` | mGBA |
| Pokémon Pinball | [pret/pokepinball](https://github.com/pret/pokepinball) | `pokemon-pinball` | mGBA |
| Pokémon TCG | [pret/poketcg](https://github.com/pret/poketcg) | `pokemon-tcg` | mGBA |
| Pokémon Ruby / Sapphire | [pret/pokeruby](https://github.com/pret/pokeruby) | `pokemon-ruby`, `pokemon-sapphire` | mGBA |
| Pokémon Emerald | [pret/pokeemerald](https://github.com/pret/pokeemerald) | `pokemon-emerald` | mGBA |
| Pokémon FireRed / LeafGreen | [pret/pokefirered](https://github.com/pret/pokefirered) | `pokemon-firered`, `pokemon-leafgreen` | mGBA |
| Pokémon Pinball R&S | [pret/pokepinballrs](https://github.com/pret/pokepinballrs) | `pokemon-pinball-rs` | mGBA |
| Pokémon MD Red | [pret/pmd-red](https://github.com/pret/pmd-red) | `pokemon-md-red` | mGBA |
| Pokémon Diamond / Pearl | [pret/pokediamond](https://github.com/pret/pokediamond) | `pokemon-diamond`, `pokemon-pearl` | melonDS |
| Pokémon Platinum | [pret/pokeplatinum](https://github.com/pret/pokeplatinum) | `pokemon-platinum` | melonDS |
| Pokémon HeartGold / SoulSilver | [pret/pokeheartgold](https://github.com/pret/pokeheartgold) | `pokemon-heartgold`, `pokemon-soulsilver` | melonDS |
| Pokémon MD Sky | [pret/pmd-sky](https://github.com/pret/pmd-sky) | `pokemon-md-sky` | melonDS |
| **Pokémon Snap** | [ethteck/pokemonsnap](https://github.com/ethteck/pokemonsnap) + [Snap64Recomp](https://github.com/JackandBeans/Snap64Recomp) | `pokemon-snap` | **port nativo** (precisa de Vulkan) |

Ficaram de fora por enquanto:

- **Pokémon Stadium 1 e 2, Puzzle League, Battle Revolution, PokéPark, Rumble:** as
  descompilações estão incompletas e não têm port. Dá para adicionar como jogo de emulador (veja
  [ADICIONAR-JOGOS.md](ADICIONAR-JOGOS.md)); o Stadium precisa do Transfer Pak, que nem todo
  emulador suporta bem.
- **Pokémon Moon** ([gradenGnostic/pokemoon](https://github.com/gradenGnostic/pokemoon)): cerca
  de 16% descompilado. O "runtime de PC" do projeto ainda não roda o jogo.
- **Pokémon Gold SpaceWorld Demo, Emerald (JP):** protótipo e versão japonesa.

### Controles nos Pokémon

Todos precisam de controle (Bluetooth ou os controles na tela do Moonlight), porque andar exige o
direcional. Nos jogos de **DS**, a tela de baixo também responde ao **toque**: o toque do celular
chega ao melonDS como clique.

### Saves

O mGBA e o melonDS gravam o save ao lado da ROM. Por isso a ROM é copiada para
`~/AllGames/jogos/<id>/`, e o save fica em `~/AllGames/jogos/<id>/<id>.sav`, no PC. Os save states
(`.ss1`, `.ml1`...) também entram nas cópias de segurança.

## Resident Evil 4

A lista aponta para [adonis-singh/re4](https://github.com/adonis-singh/re4). O projeto é uma
descompilação **matching completa**, mas do **protótipo de debug** do RE4 de GameCube (`G4BE08`,
"Nov 25 2004", dois discos). Ao compilar, ele gera **os mesmos arquivos do disco** (`main.dol` e
as 114 overlays) e confere com SHA-1. Isso significa que:

- não existe um executável de PC saindo dessa descompilação;
- para compilar, ele exige os discos do **protótipo de debug**, não os do jogo vendido nas lojas;
- o resultado roda no Dolphin, exatamente como o disco original.

Por isso o AllGames oferece o RE4 de dois jeitos que funcionam hoje:

### `re4`: GameCube no Dolphin

1. Faça o dump dos seus dois discos do RE4 de GameCube (por exemplo, com um Wii e o CleanRip).
2. Coloque em `~/AllGames/originais` com os nomes `re4-disco1.iso` e `re4-disco2.iso`. Também
   servem `.rvz`, `.gcm` e `.ciso`.
3. `allgames instalar re4`

A receita cria uma playlist `.m3u` com os dois discos e liga a troca automática do Dolphin. Quando o
jogo pedir o disco 2, ele troca sozinho. O save fica no cartão de memória virtual do Dolphin, no PC
(`~/.var/app/org.DolphinEmu.dolphin-emu/data/dolphin-emu/GC/`).

### `re4-steam`: versão de PC

Se você tem o **Resident Evil 4 (2014)** na Steam (app 254700), `allgames instalar re4-steam`
abre a instalação na Steam e o jogo roda pelo Proton. Os saves ficam na pasta da Steam no PC e na
nuvem da Steam.

### E o Resident Evil 2?

A lista também tem o [OpenBiohazard2](https://github.com/OpenBiohazard2/OpenBiohazard2), uma
reimplementação em andamento do RE2 que usa os arquivos da versão de PC. Quando ele ficar jogável
do começo ao fim, dá para adicioná-lo como `port`.
