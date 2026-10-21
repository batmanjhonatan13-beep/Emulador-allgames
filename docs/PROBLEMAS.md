# Problemas comuns

Comece sempre por `allgames doutor` e pelos logs:

```bash
journalctl --user -u app-dev.lizardbyte.app.Sunshine -e   # log do Sunshine
cat ~/AllGames/logs/<id>.log                              # log do jogo
```

## Tela preta ou "nenhum display" no celular

- O Pop!\_OS 24.04 usa o COSMIC, que roda em Wayland. O Sunshine precisa da captura **KMS**, liberada
  por `sudo setcap cap_sys_admin+p "$(readlink -f "$(which sunshine)")"`. O
  `scripts/instalar-host.sh` já faz isso; repita depois de atualizar o Sunshine.
- No painel do Sunshine (https://localhost:47990 → Configuration → Advanced), teste os métodos de
  captura `kms` e `portal` e veja no log qual funcionou.
- A sessão precisa estar **aberta** no PC. Ative o login automático e desative a suspensão da tela
  nas configurações de energia.
- **PC sem monitor:** a placa de vídeo precisa enxergar uma tela. Use um adaptador "dummy plug"
  HDMI/DisplayPort barato, ou deixe o monitor conectado (pode ficar desligado).

## O controle ou o toque não funcionam

- `/dev/uinput` precisa estar liberado: `allgames doutor` diz o que fazer. Depois de entrar no
  grupo `input`, saia da sessão e entre de novo.
- Alguns jogos só reconhecem o controle se ele já estiver conectado quando o jogo abre. Conecte o
  controle Bluetooth no celular antes de tocar no jogo.

## Vídeo travando ou com atraso

- Use Wi-Fi de **5 GHz** no celular e, se der, ligue o PC ao roteador por cabo.
- Diminua o bitrate no Moonlight. Fora de casa, comece com 720p e 5–10 Mbps.
- Confira se a codificação é por hardware: em `allgames doutor`, a linha "Vídeo" deve mostrar
  NVENC (NVIDIA) ou VA-API (AMD/Intel). Na NVIDIA, use a ISO do Pop!\_OS com driver NVIDIA ou instale
  `system76-driver-nvidia`. Na AMD, instale `mesa-va-drivers`.

## O jogo abre em janela ou na resolução errada

- Ative a tela cheia nas opções do jogo uma vez, abrindo-o no PC com `allgames jogar <id>`. A
  configuração fica salva.
- Ou publique com `allgames sincronizar --gamescope`: o jogo roda dentro do gamescope, em tela
  cheia e na resolução que o celular pediu.

## O jogo não abre

- Rode `allgames jogar <id>` num terminal do PC e leia `~/AllGames/logs/<id>.log`.
- **Abre pelo terminal mas não pelo celular:** o serviço do Sunshine pode não ter as variáveis da
  sessão gráfica. Rode `systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR`
  e reinicie o serviço (`systemctl --user restart app-dev.lizardbyte.app.Sunshine`).
- **Ports da HarbourMasters (soh, 2ship, starship, spaghettikart):** na primeira execução o jogo
  extrai os recursos da ROM e pode pedir que você escolha o arquivo. Faça essa primeira abertura
  no PC.
- **AppImage não executa:** instale a libfuse2 (`sudo apt install libfuse2t64` no 24.04). Sem
  ela o AllGames extrai a AppImage a cada execução, o que funciona, mas é mais lento.
- Reinstale com `allgames instalar <id>`. A receita atualiza o código e compila de novo.

## O portal (tela com as capas)

- **Não abre pelo Moonlight:** `allgames doutor` diz se há navegador (Firefox ou Chromium). Teste
  no PC com `allgames portal --kiosk`; para sair, use o botão ⏻.
- **Toque move um cursor em vez de clicar:** deixe o Moonlight em toque direto (veja
  [CELULAR.md](CELULAR.md)).
- **O controle não navega:** aperte qualquer botão. Os navegadores só mostram o controle à página
  depois do primeiro botão.
- **Capas não aparecem:** elas são baixadas do libretro-thumbnails na primeira vez e ficam em
  `~/AllGames/capas`. Sem internet, aparecem as iniciais do jogo; um PNG em `capas/<id>.png` resolve.
- **Usar outro navegador:** `ALLGAMES_NAVEGADOR=chromium allgames portal --kiosk`.

## Saves

- `allgames saves` lista o último save de cada jogo e quantas cópias existem.
- Perdeu progresso ou o save corrompeu: `allgames saves <id>` mostra as cópias, e
  `allgames restaurar <id> <nome>` volta para uma delas. O estado atual é guardado antes.
- "o catálogo não diz onde este jogo grava os saves": adicione o campo `saves` ao jogo em
  `catalogo/jogos.toml`.

## Pokémon não é reconhecido

- `allgames verificar pokemon-emerald` diz se achou um arquivo com a extensão certa e se o SHA-1
  bate. As ROMs aceitas são as versões americanas/europeias listadas no catálogo; ROM hacks,
  traduções e versões de outras regiões têm outro SHA-1.
- ROM compactada (`.zip`, `.7z`): descompacte antes.

## O Moonlight não mostra os jogos novos

- `allgames sincronizar` reinicia o Sunshine sozinho. Depois disso, puxe a lista para baixo no
  Moonlight ou saia e entre no PC de novo.
- Se você já tinha um app no Sunshine com o mesmo nome, o AllGames não o substitui e avisa. Renomeie
  o seu app no painel do Sunshine.
- Antes de cada alteração o AllGames guarda uma cópia: `~/.config/sunshine/apps.json.<data>.bak`.
