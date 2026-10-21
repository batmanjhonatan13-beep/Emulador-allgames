# AllGames: cloud gaming pessoal

Os jogos rodam e **salvam no seu PC com Pop!\_OS**, e você joga **pelo celular**, em casa ou fora
dela, como no Xbox Cloud Gaming. A diferença é que o "servidor na nuvem" é o seu próprio computador.

Os jogos vêm de projetos de **descompilação** (lista em
[SamidyFR/Game-Decompilations](https://github.com/SamidyFR/Game-Decompilations)). Esses projetos
reconstroem o código-fonte de jogos antigos. Quando a descompilação virou um **port nativo para
PC**, o AllGames compila ou baixa o port. Quando ela só reconstrói o jogo original, ele roda num
emulador. Tudo aparece numa **tela com as capas dos jogos, no estilo do Game Pass**, que você usa
pelo celular tocando na tela ou com controle.

```
 ┌──────────────── PC (Pop!_OS) ─────────────────┐            ┌──────── Celular ────────┐
 │                                                │            │                         │
 │  ~/AllGames/originais  (suas ROMs/ISOs)        │            │  App Moonlight          │
 │          │                                     │   vídeo    │   └─ "AllGames"         │
 │          ▼                                     │ ─────────► │      tela com as capas, │
 │  port nativo / emulador ◄── portal AllGames ◄──┼─ Sunshine  │      toque ou controle  │
 │          │                  (tela de capas)    │ ◄───────── │                         │
 │          ▼                                     │  toque e   │                         │
 │  saves no PC + cópias em ~/AllGames/backups    │  controle  │                         │
 └────────────────────────────────────────────────┘            └─────────────────────────┘
              Wi-Fi de casa, ou Tailscale (VPN privada) para jogar no 4G/5G
```

| Peça | Função |
|---|---|
| [Sunshine](https://github.com/LizardByte/Sunshine) | servidor de streaming no PC: captura a tela, codifica o vídeo na GPU e recebe toque e controle do celular |
| [Moonlight](https://moonlight-stream.org) | app do celular (Android e iOS) que mostra o PC com pouco atraso |
| **Portal AllGames** | a tela com as capas, estilo Game Pass. É o app "AllGames" no Moonlight |
| `allgames` | catálogo, instalação de cada jogo, saves e publicação no Sunshine |
| [Tailscale](https://tailscale.com) | rede privada entre o PC e o celular para jogar fora de casa sem abrir portas |

## O portal (tela com as capas)

- **Início:** destaque com o último jogo, "Continue jogando", "Prontos para jogar" e uma fileira
  por coleção (Pokémon, Resident Evil, Nintendo 64...).
- **Biblioteca:** todos os jogos com filtros: instalados, **jogáveis no toque**, **com
  controle** e por console.
- **Toque ou controle, como no Game Pass:** cada jogo mostra se dá para jogar tocando na tela ou se
  precisa de controle. Se você abrir um jogo de controle sem controle conectado, o portal avisa. É só
  conectar um controle Bluetooth ou ativar os controles na tela do Moonlight.
- **Navegação:** toque, setas do teclado ou controle (direcional, A seleciona, B volta, LB/RB
  trocam de aba).
- Ao sair do jogo, você volta para o portal. O portal mostra quando foi o último save de cada jogo.

## O progresso fica salvo no PC

O celular só recebe o vídeo: o jogo e o save ficam no PC. Para cada jogo, o catálogo diz onde o save
fica, e o AllGames:

- mostra os saves: `allgames saves` e `allgames saves pokemon-emerald`;
- faz uma **cópia de segurança antes de cada partida** em `~/AllGames/backups/<jogo>/`, guardando
  as 10 últimas (só copia quando algo mudou);
- volta para uma cópia: `allgames restaurar pokemon-emerald` (antes, guarda o estado atual).

Nos emuladores, a ROM é copiada para `~/AllGames/jogos/<jogo>/` e o save (`.sav`) fica ao lado dela.

## Você precisa ter os jogos

As descompilações **não incluem o jogo**: gráficos, sons e fases saem da **sua cópia original**
(ROM extraída do seu cartucho, ISO do seu disco, arquivos da sua instalação). O AllGames nunca baixa
ROMs ou dados de jogos. Coloque seus arquivos em `~/AllGames/originais`. Para os Pokémon, o **nome
do arquivo não importa**: cada ROM é reconhecida pelo SHA-1, o mesmo que as descompilações do
[pret](https://github.com/pret) usam para conferir o resultado.

## Instalação

```bash
git clone https://github.com/batmanjhonatan13-beep/Emulador-allgames.git ~/Emulador-allgames
cd ~/Emulador-allgames
./scripts/instalar-host.sh        # Sunshine, captura de tela, controles, serviço e portal
./scripts/instalar-tailscale.sh   # opcional: jogar fora de casa
allgames doutor                   # confere se está tudo certo
```

Depois:

1. No PC, abra **https://localhost:47990** e crie o usuário e a senha do Sunshine.
2. No celular, instale o **Moonlight**. Toque no PC e digite o PIN em https://localhost:47990/pin.
3. Copie suas ROMs/ISOs para `~/AllGames/originais` e instale:

   ```bash
   allgames verificar                  # o que foi reconhecido e o que falta
   allgames instalar pokemon-emerald   # ou: allgames instalar --todos
   ```

4. No Moonlight, toque em **AllGames** e escolha o jogo pela capa.

## Jogos do catálogo

**Pokémon** (22 jogos). As descompilações do pret reconstroem a ROM idêntica à original, então
eles rodam no emulador com a sua ROM:

| Console | Jogos | Como roda |
|---|---|---|
| Game Boy / Color | Red, Blue, Yellow, Gold, Silver, Crystal, Pinball, Trading Card Game | mGBA |
| Game Boy Advance | Ruby, Sapphire, Emerald, FireRed, LeafGreen, Pinball R&S, Mystery Dungeon Red | mGBA |
| Nintendo DS | Diamond, Pearl, Platinum, HeartGold, SoulSilver, Mystery Dungeon Sky | melonDS (a tela de baixo responde ao toque) |
| Nintendo 64 | **Pokémon Snap**: port **nativo** para PC ([Snap64Recomp](https://github.com/JackandBeans/Snap64Recomp)) | sem emulador |

**Resident Evil 4**: a descompilação da lista ([adonis-singh/re4](https://github.com/adonis-singh/re4))
reconstrói os arquivos do **protótipo de debug de 2004 do GameCube**, mas não é um port para PC.
Então o RE4 entra de dois jeitos:

| ID | Como roda | O que você precisa |
|---|---|---|
| `re4` | Dolphin, com troca automática dos 2 discos | `re4-disco1.iso` e `re4-disco2.iso` (dumps dos seus discos de GameCube) |
| `re4-steam` | versão de PC (2014) pela Steam/Proton | o jogo na sua conta Steam |

Detalhes e o que mais existe na lista: [docs/POKEMON-E-RE4.md](docs/POKEMON-E-RE4.md).

**Outros:** Super Mario 64, Zelda Ocarina of Time e Majora's Mask, Star Fox 64, Mario Kart 64,
Perfect Dark (ports nativos), Diablo (DevilutionX: anda e ataca tocando na tela, e roda a demo sem
arquivo nenhum) e Metroid Prime (Dolphin).

`allgames listar` mostra tudo. Para adicionar jogos: [docs/ADICIONAR-JOGOS.md](docs/ADICIONAR-JOGOS.md).

## Comandos

| Comando | O que faz |
|---|---|
| `allgames listar` | catálogo e situação de cada jogo |
| `allgames verificar [ID...]` | confere os arquivos originais e as versões |
| `allgames instalar ID... \| --todos` | instala o jogo e atualiza o Sunshine |
| `allgames portal` | abre a tela de capas no navegador do PC (`--kiosk` é o que o Sunshine usa) |
| `allgames saves [ID]` | onde cada jogo salva, último save e cópias |
| `allgames backup [ID...]` | copia os saves agora |
| `allgames restaurar ID [NOME]` | volta os saves para uma cópia |
| `allgames sincronizar [--gamescope \| --no-gamescope]` | republica o portal e os jogos no Sunshine |
| `allgames jogar ID` | abre um jogo (faz o backup antes). Log em `~/AllGames/logs/ID.log` |
| `allgames doutor` | confere Sunshine, captura, GPU, controles, Tailscale e navegador |

## Mais documentação

- [docs/CELULAR.md](docs/CELULAR.md): Moonlight, portal, toque e controle, jogar fora de casa
- [docs/POKEMON-E-RE4.md](docs/POKEMON-E-RE4.md): o que a lista de descompilações tem de Pokémon e RE4
- [docs/ADICIONAR-JOGOS.md](docs/ADICIONAR-JOGOS.md): como cada tipo de descompilação vira jogo
- [docs/PROBLEMAS.md](docs/PROBLEMAS.md): tela preta, atraso, controle, saves

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -t .
shellcheck -x scripts/*.sh && (cd receitas && shellcheck -s bash ./*.sh)
```
