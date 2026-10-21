# AllGames: cloud gaming pessoal

Um serviço que fica no seu **PC com Pop!\_OS**: os jogos rodam e **salvam no PC**, e você joga
**pelo celular**, na rede de casa (ou fora dela, com o Tailscale). É como o Xbox Cloud Gaming, mas
o "servidor na nuvem" é o seu computador.

Tudo aparece numa **tela com as capas, no estilo do Game Pass**, que você usa tocando no celular
ou com controle:

- **ROMs, igual ao R36S/ArkOS:** uma pasta por console (`roms/snes`, `roms/psx`, `roms/ps2`,
  `roms/switch`...). Toda ROM colocada lá aparece sozinha, com capa, e abre no emulador certo:
  Switch, PS1, PS2, PSP, Xbox, GameCube/Wii, 3DS, DS e mais de 25 consoles retrô.
- **Jogos de PC:** a sua biblioteca da **Steam** e, pelo Heroic, da **Epic Games, GOG e Amazon**.
  Instale, desinstale e jogue pelo celular. Os jogos de Windows rodam pelo Proton.
- **Jogos descompilados:** ports nativos para PC feitos a partir das descompilações da lista
  [SamidyFR/Game-Decompilations](https://github.com/SamidyFR/Game-Decompilations) (Super Mario 64,
  Zelda, Pokémon Snap...), mais os Pokémon e o Resident Evil 4.

```
 ┌──────────────────── PC (Pop!_OS, sempre ligado) ────────────────────┐        ┌──── Celular ────┐
 │                                                                      │        │                 │
 │  ~/AllGames/roms/<console>  ──► emuladores (RetroArch, PCSX2, ...)   │        │  App Moonlight  │
 │  Steam / Heroic (Epic, GOG) ──► jogos de PC (Proton)                 │ vídeo  │   └ "AllGames"  │
 │  jogos descompilados        ──► ports nativos                        │ ─────► │     tela com as │
 │                    ▲                                                 │        │     capas       │
 │          portal AllGames (tela de capas) ◄── Sunshine ◄──────────────┼─────── │  toque/controle │
 │                                                                      │        │                 │
 │  saves no PC + cópia de segurança antes de cada partida              │        │                 │
 └──────────────────────────────────────────────────────────────────────┘        └─────────────────┘
```

| Peça | Função |
|---|---|
| [Sunshine](https://github.com/LizardByte/Sunshine) | transmite a tela do PC (vídeo codificado na GPU) e recebe toque e controle do celular |
| [Moonlight](https://moonlight-stream.org) | app do celular (Android e iOS) que mostra o PC com pouco atraso |
| **Portal AllGames** | a tela com as capas, estilo Game Pass. É o app "AllGames" no Moonlight |
| `allgames` | biblioteca (ROMs, lojas, catálogo), emuladores, saves e publicação no Sunshine |

## Instalação

```bash
git clone https://github.com/batmanjhonatan13-beep/Emulador-allgames.git ~/Emulador-allgames
cd ~/Emulador-allgames
./scripts/instalar-host.sh       # Sunshine, captura de tela, controles e o portal
./scripts/instalar-lojas.sh      # Steam e Heroic (Epic, GOG, Amazon)
./scripts/modo-servidor.sh       # PC sem suspender, Wake-on-LAN, login automático
allgames roms                    # cria as pastas de ROMs (mesmos nomes do ArkOS)
allgames doutor                  # confere se está tudo certo
```

Depois:

1. No PC, abra **https://localhost:47990** e crie o usuário e a senha do Sunshine.
2. No celular, instale o **Moonlight**. Na mesma rede Wi-Fi o PC aparece sozinho. Toque nele e
   digite o PIN em https://localhost:47990/pin.
3. Copie as suas ROMs para `~/AllGames/roms/<console>` (dá para copiar a pasta `roms` inteira do
   cartão do R36S) e rode `allgames emuladores instalar`.
4. Entre nas suas contas na Steam e no Heroic, no PC.
5. No Moonlight, toque em **AllGames** e escolha o jogo.

## O portal

- **Início:** o último jogo em destaque, "Continue jogando", "Prontos para jogar" e uma fileira por
  coleção (Super Nintendo, PlayStation, Steam, Epic Games, Pokémon...).
- **Biblioteca:** todos os jogos, com filtros (instalados, jogáveis no toque, com controle, ROMs,
  lojas e por console).
- **Toque ou controle, como no Game Pass:** cada capa mostra como jogar. Abrir um jogo de controle
  sem controle conectado mostra um aviso.
- **Instalar e desinstalar pelo celular:** jogos da Steam, do Heroic e emuladores que faltam.
- Navegação por toque, teclado ou controle (direcional, A seleciona, B volta, LB/RB trocam de aba).
  Ao sair do jogo, você volta para o portal.

## Os saves ficam no PC

O celular só recebe o vídeo. O jogo e o progresso ficam no PC, e o AllGames faz uma **cópia de
segurança antes de cada partida** em `~/AllGames/backups` (as 10 últimas por jogo, só quando algo
mudou). Nas ROMs do RetroArch, o save fica ao lado da ROM, como no ArkOS. Detalhes em
[docs/ROMS-E-EMULADORES.md](docs/ROMS-E-EMULADORES.md).

## E o Game Pass?

Os jogos do **PC Game Pass não rodam no Linux**: eles dependem do app Xbox/Microsoft Store do
Windows. Com o **Game Pass Ultimate**, o **Xbox Cloud Gaming** já roda direto no celular
(xbox.com/play), sem o PC. Para usar o seu hardware, a saída é ter o Windows em dual boot com o
Sunshine. Explicação completa em [docs/LOJAS.md](docs/LOJAS.md).

## Você precisa ter os jogos

O AllGames **não baixa ROMs, BIOS, chaves ou firmware**: use os dos seus cartuchos, discos e
consoles. As descompilações também não incluem o jogo: os gráficos e sons saem da sua cópia
original, em `~/AllGames/originais`.

## Comandos

| Comando | O que faz |
|---|---|
| `allgames roms [--todos]` | cria as pastas por console e mostra quantas ROMs há em cada |
| `allgames emuladores [instalar [SISTEMA...]]` | lista os emuladores ou instala os que as suas ROMs pedem |
| `allgames lojas [--detalhes]` | jogos encontrados na Steam e no Heroic |
| `allgames listar` / `verificar` / `instalar ID` | jogos descompilados do catálogo |
| `allgames portal [--kiosk]` | a tela de capas (`--kiosk` é o que o Sunshine usa) |
| `allgames saves [ID]` / `backup` / `restaurar ID` | saves e cópias de segurança |
| `allgames sincronizar` | publica o portal e os jogos do catálogo no Sunshine |
| `allgames jogar ID` | abre um jogo (ROM, loja ou catálogo). Log em `~/AllGames/logs/` |
| `allgames doutor` | confere Sunshine, captura, GPU, controles, rede e navegador |

## Documentação

- [docs/ROMS-E-EMULADORES.md](docs/ROMS-E-EMULADORES.md): pastas, consoles, BIOS, Switch, PS2,
  Xbox, saves e capas
- [docs/LOJAS.md](docs/LOJAS.md): Steam, Epic, GOG, Amazon, Ubisoft, EA e Game Pass
- [docs/MODO-SERVIDOR.md](docs/MODO-SERVIDOR.md): deixar o PC ligado e acordá-lo pelo celular
- [docs/CELULAR.md](docs/CELULAR.md): Moonlight, portal, toque e controle, jogar fora de casa
- [docs/POKEMON-E-RE4.md](docs/POKEMON-E-RE4.md) e [docs/ADICIONAR-JOGOS.md](docs/ADICIONAR-JOGOS.md):
  jogos descompilados
- [docs/PROBLEMAS.md](docs/PROBLEMAS.md): tela preta, atraso, controle, saves

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -t .
shellcheck -x scripts/*.sh && (cd receitas && shellcheck -s bash ./*.sh)
```
