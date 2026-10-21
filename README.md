# AllGames: cloud gaming pessoal

Os jogos rodam no **seu PC com Pop!\_OS**, e você joga **pelo celular**, em casa ou fora dela,
como no Xbox Cloud Gaming. A diferença é que o "servidor na nuvem" é o seu próprio computador.

Os jogos vêm de projetos de **descompilação** (lista em
[SamidyFR/Game-Decompilations](https://github.com/SamidyFR/Game-Decompilations)). Esses projetos
reconstroem o código-fonte de jogos antigos, e muitos já ganharam **ports nativos para PC/Linux**.
O AllGames compila ou baixa esses ports, usa um emulador quando não existe port e publica tudo
numa lista com capas para o celular.

```
 ┌──────────────── PC (Pop!_OS) ────────────────┐            ┌──────── Celular ────────┐
 │                                               │            │                         │
 │  ~/AllGames/originais  (suas ROMs/ISOs)       │            │  App Moonlight          │
 │          │                                    │            │  (ou navegador, opc.)   │
 │          ▼                                    │   vídeo    │                         │
 │  allgames instalar ──► port nativo / emulador │  H.264/    │  lista de jogos c/ capa │
 │          │                 ▲                  │  HEVC/AV1  │  toque / controle BT    │
 │          ▼                 │ abre o jogo      │ ─────────► │                         │
 │  allgames sincronizar ──► Sunshine ───────────┼──────────► │                         │
 │                           (captura a tela e   │ ◄───────── │                         │
 │                            codifica na GPU)   │  controles │                         │
 └───────────────────────────────────────────────┘            └─────────────────────────┘
              Wi-Fi de casa, ou Tailscale (VPN privada) para jogar no 4G/5G
```

| Peça | Função |
|---|---|
| [Sunshine](https://github.com/LizardByte/Sunshine) | servidor de streaming no PC: captura a tela, codifica o vídeo na GPU (NVENC na NVIDIA, VA-API na AMD/Intel) e recebe os comandos do celular como um controle de Xbox virtual |
| [Moonlight](https://moonlight-stream.org) | app do celular (Android e iOS) que mostra a lista de jogos e transmite com pouco atraso |
| `allgames` (este repositório) | catálogo de jogos, receitas de instalação de cada port e publicação dos jogos no Sunshine |
| [Tailscale](https://tailscale.com) | rede privada entre o PC e o celular para jogar fora de casa sem abrir portas no roteador |
| [Moonlight Web](https://github.com/MrCreativ3001/moonlight-web-stream) (opcional) | o "site": joga pelo navegador do celular, sem instalar app |

## Você precisa ter os jogos

As descompilações **não incluem o jogo**: texturas, sons, músicas e fases saem da **sua cópia
original** (ROM extraída do seu cartucho, ISO do seu disco, arquivos da sua instalação). O AllGames
nunca baixa ROMs ou dados de jogos. Você coloca seus arquivos em `~/AllGames/originais`, e ele
confere a versão pelo SHA-1 quando o catálogo informa o hash.

## Instalação

```bash
git clone https://github.com/batmanjhonatan13-beep/Emulador-allgames.git ~/Emulador-allgames
cd ~/Emulador-allgames
./scripts/instalar-host.sh        # Sunshine, captura de tela, controles, serviço
./scripts/instalar-tailscale.sh   # opcional: jogar fora de casa
allgames doutor                   # confere se está tudo certo
```

Depois:

1. No PC, abra **https://localhost:47990** e crie o usuário e a senha do Sunshine.
2. No celular, instale o **Moonlight**. Na mesma rede Wi-Fi o PC aparece sozinho. Toque nele e
   digite o PIN em https://localhost:47990/pin.
3. Copie os arquivos dos seus jogos para `~/AllGames/originais` com o nome que o catálogo pede:

   ```bash
   allgames verificar          # mostra o que falta e o nome esperado de cada arquivo
   allgames instalar sm64      # compila/baixa o jogo e publica no Sunshine
   allgames instalar --todos   # instala todos os que já têm os originais
   ```

4. No Moonlight, toque no PC: os jogos aparecem com capa. Toque em um para jogar.

## Comandos

| Comando | O que faz |
|---|---|
| `allgames listar` | catálogo e situação de cada jogo (instalado / falta o original / pronto) |
| `allgames verificar [ID...]` | confere os arquivos originais e as versões |
| `allgames instalar ID... \| --todos` | roda a receita do jogo e atualiza o Sunshine |
| `allgames sincronizar [--gamescope \| --no-gamescope]` | republica os jogos instalados no Sunshine (preserva os apps que você criou à mão) |
| `allgames jogar ID` | abre o jogo; é o comando que o Sunshine chama. Saída em `~/AllGames/logs/ID.log` |
| `allgames doutor` | confere Sunshine, captura KMS, GPU, controles, Tailscale |

## Jogos do catálogo

| ID | Jogo | Como roda | Arquivo em `~/AllGames/originais` |
|---|---|---|---|
| `sm64` | Super Mario 64 | port [sm64ex](https://github.com/sm64pc/sm64ex), compilado | `sm64.us.z64` |
| `soh` | Zelda: Ocarina of Time | port [Ship of Harkinian](https://github.com/HarbourMasters/Shipwright) | `oot.z64` |
| `2ship` | Zelda: Majora's Mask | port [2 Ship 2 Harkinian](https://github.com/HarbourMasters/2ship2harkinian) | `mm.z64` |
| `starship` | Star Fox 64 | port [Starship](https://github.com/HarbourMasters/Starship) | `sf64.z64` |
| `spaghettikart` | Mario Kart 64 | port [SpaghettiKart](https://github.com/HarbourMasters/SpaghettiKart) | `mk64.z64` |
| `perfect-dark` | Perfect Dark | port [fgsfdsfgs/perfect_dark](https://github.com/fgsfdsfgs/perfect_dark), compilado | `pd.ntsc-final.z64` |
| `devilutionx` | Diablo | port [DevilutionX](https://github.com/diasurgical/DevilutionX) (Flatpak) | `DIABDAT.MPQ` (opcional: sem ele roda a demo) |
| `metroid-prime` | Metroid Prime | emulador Dolphin (a descompilação ainda não tem port) | `metroid-prime.iso` / `.rvz` |

**Teste rápido sem ROM nenhuma:** `allgames instalar devilutionx` instala o Diablo com a demo
que vem junto e já deixa o jogo na lista do celular.

Para adicionar outros jogos da lista de descompilações, veja [docs/ADICIONAR-JOGOS.md](docs/ADICIONAR-JOGOS.md).

## Mais documentação

- [docs/CELULAR.md](docs/CELULAR.md): configurar o Moonlight, controles na tela ou Bluetooth, jogar
  fora de casa e pelo navegador
- [docs/ADICIONAR-JOGOS.md](docs/ADICIONAR-JOGOS.md): como cada tipo de descompilação vira um jogo
  jogável e como escrever uma receita
- [docs/PROBLEMAS.md](docs/PROBLEMAS.md): tela preta, atraso, controle que não responde, PC sem
  monitor

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -t .
shellcheck -x scripts/*.sh && (cd receitas && shellcheck -s bash ./*.sh)
```
