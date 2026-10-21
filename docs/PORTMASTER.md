# PortMaster (os ports do R36S)

O [PortMaster](https://portmaster.games/games.html) é a loja de ports dos portáteis como o R36S:
jogos de PC adaptados (Celeste, Stardew Valley, Cave Story, 2048...) que você pesquisa, baixa,
joga e desinstala. O AllGames faz o mesmo pelo portal, com o jogo rodando no PC.

## No portal

1. **Biblioteca** → filtro **PortMaster** (ou digite o nome na busca).
2. Abra o port e toque em **Instalar**. O AllGames baixa do catálogo oficial, confere o arquivo e
   instala com o próprio instalador do PortMaster.
3. Toque em **Jogar**. Para sair, **segure Select + Start** por um segundo, como no R36S.
4. **Desinstalar** fica no mesmo lugar.

Precisa de internet para pesquisar e instalar; os ports instalados abrem sem internet.

## Quais ports aparecem

O PortMaster foi feito para portáteis ARM, e nem todo port tem versão para PC. O portal mostra só
os que rodam em **x86_64**, os mesmos que funcionam no Steam Deck: cerca de 340 dos mais de mil do
catálogo.

### "Precisa dos arquivos do jogo"

Ports de jogos comerciais (Stardew Valley, Celeste, Terraria...) não trazem o jogo, só a
adaptação. Para esses o portal mostra um aviso com as instruções do próprio PortMaster: em geral,
copiar os arquivos da sua cópia do jogo (por exemplo, da pasta da Steam ou do GOG) para
`roms/ports/<pasta do port>/` (no Docker, a pasta `ROMS` do `docker/.env`). Os ports gratuitos
("prontos para jogar") abrem direto.

## Saves

Ficam na pasta de cada port, em `roms/ports/<pasta do port>/` (em geral `saves/`, `savedata/` ou
`conf/`). O AllGames faz a cópia de segurança antes de cada partida, como nos outros jogos.

## Pelo terminal

```bash
allgames portmaster                 # lista os ports que rodam no PC (✔ = instalado)
allgames portmaster celeste         # pesquisa
allgames portmaster instalar 2048   # instala (o nome é o do arquivo .zip, com ou sem .zip)
allgames portmaster desinstalar 2048
```

No Docker: `docker exec -it -u steamheadless allgames allgames portmaster ...`

## Sem Docker

No Docker o PortMaster já vem instalado. Direto no Pop!\_OS:

```bash
./scripts/instalar-portmaster.sh
```

Ele instala o PortMaster em `/opt/tools/PortMaster` e cria `/roms` apontando para
`~/AllGames/roms` (os caminhos que o PortMaster procura), mais as bibliotecas que os ports usam.

## Como funciona por dentro

- O catálogo vem de `PortMaster-Info/ports.json` e fica guardado por 6 horas em
  `~/AllGames/.cache-portmaster.json`.
- O instalador é o `harbourmaster` do PortMaster, então os ports ficam iguais aos de um R36S.
- Num PC, o PortMaster não reconhece o aparelho. O AllGames cria um `mod_<sistema>.txt` que usa o
  controle virtual de Xbox 360 do Sunshine e troca as ferramentas de ARM (como o `gptokeyb`)
  pelas versões para PC que vêm no próprio PortMaster.
