# AllGames: cloud gaming pessoal

Um serviço que fica no seu **PC com Pop!\_OS**: os jogos rodam e **salvam no PC**, e você joga
**pelo celular**, na rede de casa (ou fora dela, com o Tailscale). É como o Xbox Cloud Gaming, mas
o "servidor na nuvem" é o seu computador. Vem pronto numa **imagem Docker**: o PC só precisa do
Docker e do driver da placa de vídeo.

Tudo aparece numa **tela com as capas, no estilo do Game Pass**, que você usa tocando no celular
ou com controle:

- **ROMs, igual ao R36S/ArkOS:** uma pasta por console (`roms/snes`, `roms/psx`, `roms/ps2`,
  `roms/switch`...). Toda ROM colocada lá aparece sozinha, com capa, e abre no emulador certo:
  Switch (Eden), PS1, PS2, PSP, Xbox, GameCube/Wii, 3DS, DS e mais de 25 consoles retrô.
- **Clique e joga:** os emuladores se instalam e se configuram sozinhos. Segurar **Select +
  Start** sai do jogo salvando, e na próxima vez ele continua de onde parou.
- **PortMaster:** pesquise, instale, jogue e desinstale os ports do R36S que rodam em PC.
- **Jogos de PC:** a sua biblioteca da **Steam** e, pelo Heroic, da **Epic Games, GOG e Amazon**.
  Instale, desinstale e jogue pelo celular. Os jogos de Windows rodam pelo Proton.
- **Downloads e disco:** veja o progresso dos downloads, quanto espaço sobra em cada disco e se o
  jogo cabe; pause e continue (Epic pelo portal, Steam pela tela de downloads dela) e continue
  baixando enquanto joga outro jogo.
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
| `allgames` | biblioteca (ROMs, lojas, catálogo, PortMaster), emuladores, downloads, saves e publicação no Sunshine |

## Instalação com Docker (recomendado)

```bash
git clone https://github.com/batmanjhonatan13-beep/Emulador-allgames.git ~/Emulador-allgames
cd ~/Emulador-allgames
./scripts/instalar-docker.sh     # Docker, imagem do AllGames e as pastas
./scripts/modo-servidor.sh       # opcional: PC sem suspender, Wake-on-LAN
```

Depois:

1. Abra **https://IP-DO-PC:8483** (o script mostra o endereço), aceite o aviso de certificado,
   entre com o usuário `steamheadless` e a senha temporária
   (`docker logs allgames 2>&1 | grep 'Temporary password'`) e crie a sua senha.
2. Pela mesma página, entre na **Steam** e no **Heroic** (Epic, GOG, Amazon) uma vez.
3. No celular, instale o **Moonlight**: o PC aparece sozinho na mesma rede Wi-Fi (se não aparecer,
   toque em **+** e digite o IP do PC). Pareie com o PIN.
4. Copie as ROMs para `~/AllGames/roms/<console>` (dá para copiar a pasta `roms` inteira do
   cartão do R36S). Os emuladores já se instalam sozinhos na primeira vez que o container liga.
5. No Moonlight, toque em **AllGames** e escolha o jogo.

Pastas, atualização e problemas: [docs/DOCKER.md](docs/DOCKER.md).

## Instalação no Windows

Para quem usa Windows 10 ou 11 (sem Docker: o Sunshine, o RetroArch e o AllGames rodam direto no
Windows). Abra o **PowerShell** e cole:

```powershell
irm https://raw.githubusercontent.com/batmanjhonatan13-beep/Emulador-allgames/ccr-f2ccb85d-qka26y/scripts/instalar-windows.ps1 | iex
```

O script pede permissão de administrador, instala tudo pelo winget, pergunta se você quer copiar os
seus jogos de uma pasta e cria o usuário do Sunshine. No Windows o celular mostra a própria tela do
PC. O passo a passo para quem nunca usou está no [guia em PDF](docs/AllGames-Guia.pdf).

## Instalação sem Docker

```bash
./scripts/instalar-host.sh       # Sunshine, captura de tela, controles e o portal
./scripts/instalar-lojas.sh      # Steam, Heroic (Epic, GOG, Amazon) e legendary
./scripts/instalar-portmaster.sh # PortMaster
allgames preparar                # pastas de ROMs e todos os emuladores
allgames doutor                  # confere se está tudo certo
```

Depois, crie o usuário do Sunshine em **https://localhost:47990**, pareie o Moonlight (PIN em
https://localhost:47990/pin) e entre nas contas da Steam e do Heroic no PC.

## O portal

- **Início:** o último jogo em destaque, "Continue jogando", "Prontos para jogar" e uma fileira por
  coleção (Super Nintendo, PlayStation, Steam, Epic Games, Pokémon...).
- **Biblioteca:** todos os jogos, com busca e filtros (instalados, jogáveis no toque, com
  controle, ROMs, lojas, PortMaster e por console).
- **Downloads:** espaço livre em cada disco e o progresso de cada download, com pausa.
- **Toque ou controle, como no Game Pass:** cada capa mostra como jogar. Abrir um jogo de controle
  sem controle conectado mostra um aviso.
- **Instalar e desinstalar pelo celular:** jogos da Steam, do Heroic e emuladores que faltam.
- Navegação por toque, teclado ou controle (direcional, A seleciona, B volta, LB/RB trocam de aba).
  Ao sair do jogo (Select + Start nos emuladores), você volta para o portal.

## Os saves ficam no PC

O celular só recebe o vídeo. O jogo e o progresso ficam no PC, e o AllGames faz uma **cópia de
segurança antes de cada partida** em `~/AllGames/backups` (as 10 últimas por jogo, só quando algo
mudou). Nas ROMs do RetroArch, o save fica ao lado da ROM, como no ArkOS, e sair do jogo grava o
estado para continuar de onde parou. Detalhes em
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
| `allgames emuladores [instalar [SISTEMA...] [--todos]]` | lista os emuladores ou instala os que as suas ROMs pedem |
| `allgames preparar [--lojas]` | pastas, PortMaster e todos os emuladores (o Docker roda isso ao ligar) |
| `allgames portmaster [busca]` / `instalar PORT` / `desinstalar PORT` | ports do PortMaster |
| `allgames lojas [--detalhes]` | jogos encontrados na Steam e no Heroic |
| `allgames listar` / `verificar` / `instalar ID` | jogos descompilados do catálogo |
| `allgames portal [--kiosk]` | a tela de capas (`--kiosk` é o que o Sunshine usa) |
| `allgames saves [ID]` / `backup` / `restaurar ID` | saves e cópias de segurança |
| `allgames sincronizar` | publica o portal e os jogos do catálogo no Sunshine |
| `allgames jogar ID` | abre um jogo (ROM, loja ou catálogo). Log em `~/AllGames/logs/` |
| `allgames doutor` | confere Sunshine, captura, GPU, controles, rede, navegador, PortMaster e Epic |

## Documentação

- [docs/DOCKER.md](docs/DOCKER.md): a imagem, as pastas (ROMs, jogos, dados), atualizar e problemas
- [docs/ROMS-E-EMULADORES.md](docs/ROMS-E-EMULADORES.md): pastas, consoles, BIOS, Switch (Eden),
  PS2, Xbox, auto-save, saves e capas
- [docs/PORTMASTER.md](docs/PORTMASTER.md): pesquisar, instalar e jogar os ports do R36S
- [docs/LOJAS.md](docs/LOJAS.md): Steam, Epic, GOG, Amazon, Ubisoft, EA, Game Pass, downloads e
  espaço em disco
- [docs/MODO-SERVIDOR.md](docs/MODO-SERVIDOR.md): deixar o PC ligado e acordá-lo pelo celular
- [docs/CELULAR.md](docs/CELULAR.md): Moonlight, portal, toque e controle, jogar fora de casa
- [docs/POKEMON-E-RE4.md](docs/POKEMON-E-RE4.md) e [docs/ADICIONAR-JOGOS.md](docs/ADICIONAR-JOGOS.md):
  jogos descompilados
- [docs/PROBLEMAS.md](docs/PROBLEMAS.md): tela preta, atraso, controle, saves

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -t .
shellcheck -x scripts/*.sh docker/*.sh && (cd receitas && shellcheck -s bash ./*.sh)
docker build -f docker/Dockerfile -t allgames:teste .
```
