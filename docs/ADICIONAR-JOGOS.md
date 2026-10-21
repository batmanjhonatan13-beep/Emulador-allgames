# Adicionando jogos da lista de descompilações

A lista [SamidyFR/Game-Decompilations](https://github.com/SamidyFR/Game-Decompilations) tem
centenas de projetos em estágios muito diferentes. Antes de adicionar um jogo, descubra em qual
destes casos ele está:

| Caso | Exemplos | Como vira jogo no AllGames | `tipo` |
|---|---|---|---|
| **Descompilação com port para PC** | Super Mario 64 → sm64ex, Ocarina of Time → Ship of Harkinian, Sonic 1/2 → RSDKv4, Doom 64 → DOOM64-EX | a receita compila o port (ou baixa a release Linux) e usa os seus arquivos originais | `port` |
| **Recompilação estática** | Majora's Mask → Zelda64Recomp, Sonic Unleashed (Xbox 360) → UnleashedRecomp | baixa a release Linux; o próprio programa pede seus arquivos na primeira execução | `recomp` |
| **Descompilação "matching", sem port** | Metroid Prime, a maioria dos jogos de PS1/PS2/GameCube | a descompilação só reconstrói o binário original, então o resultado é o próprio jogo: rode a sua cópia num emulador | `emulador` |
| **Incompleta** (⚠️ na lista) | — | ainda não dá para jogar; fique de olho no repositório | — |
| **Tem versão oficial para PC** | Resident Evil 4 (Steam) | abre pela Steam/Proton | `pc` |

Na descrição de cada repositório, procure palavras como *PC port*, *native port*, *Linux*,
*recomp* ou *builds*. Se o projeto só fala em *matching* ou *OK/checksum*, é o terceiro caso.

## Passo a passo

1. Adicione o jogo em `catalogo/jogos.toml`:

   ```toml
   [[jogo]]
   id = "sonic2"
   nome = "Sonic the Hedgehog 2"
   plataforma = "Mega Drive / Mobile"
   tipo = "port"
   colecao = "Sonic"
   descricao = "O remaster de 2013 rodando nativo no PC."
   controles = ["controle"]
   decomp = "https://github.com/Rubberduckycooly/Sonic-1-2-2013-Decompilation"
   projeto = "https://github.com/Rubberduckycooly/Sonic-1-2-2013-Decompilation"
   capa = "Sega - Mega Drive - Genesis/Sonic The Hedgehog 2 (World)"
   originais = [
     { arquivo = "Data.rsdk", descricao = "extraído da sua cópia do Sonic 2 para celular (versão 2013)" },
   ]
   ```

   - `capa` é o caminho "Sistema/Nome" no acervo
     [libretro-thumbnails](https://github.com/libretro-thumbnails). Se não achar, coloque um PNG
     em `capas/<id>.png`.
   - `controles`: `"toque"` se dá para jogar só tocando na tela (jogos de mouse), `"controle"` se
     precisa de controle. Pode ter os dois. O portal usa isso nos selos e nos filtros.
   - `saves`: onde o jogo grava o progresso, relativo a `~/AllGames/jogos/<id>` ou começando com
     `~/`. Aceita `*` e `**`. Confira com `allgames saves <id>` depois de jogar um pouco.
   - Com `sha1` nos `originais`, o arquivo é achado pelo conteúdo (`arquivo = "*.gba"` basta).

   Para vários jogos do mesmo emulador, use `receita = "mgba"` (ou `"melonds"`) em vez de criar uma
   receita: os padrões de `[receita.mgba]` no topo do catálogo valem para todos.

2. Copie `receitas/_modelo.sh` para `receitas/<id>.sh` e escreva as duas funções:
   - `instalar`: baixa ou compila o jogo dentro de `$JOGO_DIR`;
   - `executar`: abre o jogo em tela cheia, sempre com `exec` (assim o Sunshine consegue fechar o
     jogo quando você sai pelo celular).

3. Teste no PC antes de testar no celular:

   ```bash
   allgames verificar sonic2
   allgames instalar sonic2
   allgames jogar sonic2        # deve abrir em tela cheia; log em ~/AllGames/logs/sonic2.log
   ```

4. `allgames sincronizar` publica o jogo (o `instalar` já faz isso sozinho).

## Funções disponíveis nas receitas

Definidas em `receitas/_lib.sh`:

| Função | Uso |
|---|---|
| `precisa_apt pacote...` | instala pacotes do sistema que faltarem (pede sudo) |
| `precisa_flatpak app.id` | instala um app do Flathub para o seu usuário |
| `clonar URL pasta` | `git clone --recursive`, ou atualiza se já existir |
| `baixar_release dono/repo 'regex' pasta [tag]` | baixa o arquivo da release do GitHub cujo nome bate com a regex e extrai zip/tar |
| `achar pasta 'padrão'` / `achar_original 'padrão'` | localiza um arquivo sem diferenciar maiúsculas |
| `achar_executavel pasta 'padrão'` | localiza um executável (ignora bibliotecas `.so`) |
| `copiar_rom` / `rom_local` | copia a ROM para `$JOGO_DIR/<id>.<ext>`, onde o emulador grava o save |
| `rodar_appimage arquivo [args]` | executa uma AppImage, mesmo sem libfuse2 |
| `harbourmasters_instalar` / `harbourmasters_executar` | atalho para os ports da HarbourMasters |

Variáveis: `JOGO_ID`, `JOGO_DIR` (`~/AllGames/jogos/<id>`), `ORIGINAIS_DIR`
(`~/AllGames/originais`) e `ORIGINAL` (primeiro arquivo original encontrado).

## Receitas de emulador

Para o terceiro caso, use um emulador do Flathub. Exemplo com o Dolphin (veja
`receitas/metroid-prime.sh`):

```bash
APP=org.DolphinEmu.dolphin-emu
instalar() { precisa_flatpak "$APP"; }
executar() {
  exec flatpak run --filesystem="$ORIGINAIS_DIR:ro" "$APP" \
    --batch --config=Dolphin.Display.Fullscreen=True --exec="$ORIGINAL"
}
```

O `--filesystem` libera a pasta de originais para o emulador, que roda isolado no Flatpak.

| Console | Emulador (Flatpak) |
|---|---|
| GameCube / Wii | Dolphin — `org.DolphinEmu.dolphin-emu` |
| PlayStation 2 | PCSX2 — `net.pcsx2.PCSX2` |
| PSP | PPSSPP — `org.ppsspp.PPSSPP` |
| Nintendo 64 | Rosalie's Mupen GUI — `com.github.Rosalie241.RMG` |
| Game Boy / GBA | mGBA — `io.mgba.mGBA` |
| Xbox (original) | xemu — `app.xemu.xemu` (precisa dos arquivos de BIOS do seu console) |
| Vários (PS1, SNES, Mega Drive...) | RetroArch — `org.libretro.RetroArch` |

Confira o nome exato do app em [flathub.org](https://flathub.org) e as opções de linha de comando
(tela cheia, sair ao fechar o jogo) na documentação de cada emulador.
