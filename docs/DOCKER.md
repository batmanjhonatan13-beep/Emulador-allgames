# AllGames em Docker (recomendado)

O serviço inteiro numa imagem: o Pop!\_OS só precisa do **Docker** e do **driver da placa de
vídeo**. Steam, Sunshine, emuladores, Heroic, PortMaster e o portal ficam dentro do container, e
as suas coisas (ROMs, jogos e saves) ficam em pastas do PC que o container usa.

```
 Pop!_OS (só Docker + driver da GPU)
 ├── ~/AllGames/roms ─────────┐   ┌────────────── container "allgames" ──────────────┐
 ├── ~/Jogos ─────────────────┼──►│ Steam · Heroic (Epic, GOG, Amazon) · legendary   │
 └── ~/AllGames-docker ───────┘   │ RetroArch e emuladores · Eden · PortMaster       │
     (home do container,          │ Portal AllGames · Sunshine (tela virtual) ───────┼──► Moonlight
      saves, configurações)       └──────────────────────────────────────────────────┘    no celular
```

## O que vem na imagem

| Peça | Para quê |
|---|---|
| [steam-headless](https://github.com/Steam-Headless/docker-steam-headless) 2.x | base: Fedora com systemd, área de trabalho KDE, Steam, Sunshine com tela virtual que se ajusta ao celular, áudio e uma página de configuração na porta 8483 |
| AllGames | portal com as capas, ROMs, downloads, saves e os apps do Moonlight |
| [legendary](https://github.com/derrod/legendary) | downloads da Epic com progresso, pausa e retomada, com a mesma conta do Heroic |
| [PortMaster](https://portmaster.games) | os ports do R36S que rodam em PC (veja [PORTMASTER.md](PORTMASTER.md)) |

Na **primeira vez** que liga, o container baixa sozinho o RetroArch e os cores, o Eden (Switch),
o xemu (Xbox), o Azahar (3DS) e o Heroic. Eles ficam na pasta de dados e não são baixados de novo.

## Antes de começar

- **Pop!\_OS 22.04 ou mais novo** (ou outro Linux com cgroup v2, o padrão hoje).
- **Driver da placa de vídeo no PC:** NVIDIA com o driver proprietário (o Pop!\_OS tem uma imagem
  própria para NVIDIA); AMD e Intel já funcionam com o driver que vem no sistema.
- **Espaço:** uns 10 GB para a imagem e os emuladores, mais o espaço dos seus jogos.
- Se você instalou o Sunshine direto no PC antes, o script desliga ele: o do container usa as
  mesmas portas.

## Instalação

```bash
git clone https://github.com/batmanjhonatan13-beep/Emulador-allgames.git ~/Emulador-allgames
cd ~/Emulador-allgames
./scripts/instalar-docker.sh
```

O script instala o Docker (e o NVIDIA Container Toolkit, se tiver placa NVIDIA), cria
`docker/.env` com as suas pastas, constrói a imagem e liga o container. A primeira vez demora.

Depois:

1. Abra **https://IP-DO-PC:8483** (o script mostra o endereço). O navegador avisa que o
   certificado não é confiável: é normal, a página é do seu PC; avance mesmo assim. Entre com o
   usuário `steamheadless` e a senha temporária que aparece no log do container
   (`docker logs allgames 2>&1 | grep 'Temporary password'`) e crie a sua senha. Até isso ser
   feito, o Sunshine não aceita o Moonlight.
2. Pela mesma página você vê a área de trabalho do container: entre **na Steam** e **no Heroic**
   (Epic, GOG, Amazon) uma vez.
3. No celular, abra o **Moonlight**: o PC aparece sozinho na mesma rede Wi-Fi. Se não aparecer
   (no Pop!\_OS o Avahi do PC ocupa a porta de descoberta e o container desliga a dele), toque em
   **+** e digite o IP do PC. Toque nele e digite o PIN no painel do Sunshine (aberto pela página
   da porta 8483).
4. Copie as ROMs para `~/AllGames/roms/<console>` e toque em **AllGames** no Moonlight.

Para acompanhar a instalação dos emuladores na primeira vez:

```bash
docker exec allgames tail -f /home/steamheadless/AllGames/logs/preparar.log
```

## As pastas

Ficam em `docker/.env`:

| Variável | Padrão | O que guarda |
|---|---|---|
| `ROMS` | `~/AllGames/roms` | suas ROMs, uma pasta por console (`snes`, `psx`, `ps2`, `switch`...), a BIOS em `bios/` e os ports do PortMaster em `ports/`. **É aqui que você adiciona jogos** |
| `JOGOS` | `~/Jogos` | jogos da Steam (`GameLibrary/Steam`) e da Epic (`Epic`). Aponte para o disco com mais espaço |
| `DADOS` | `~/AllGames-docker` | a home do container: emuladores, Heroic, saves dos emuladores, configurações, logs e as cópias de segurança dos saves |

**Adicionar ROMs:** é só copiar para a pasta do console. Com o container ligado, elas aparecem no
portal na próxima vez que ele atualizar a lista, sem reiniciar nada. Dá para copiar pela rede
(compartilhamento do Pop!\_OS) ou direto no PC.

**Jogos que você já tinha na Steam do Pop!\_OS:** se a Steam também está instalada direto no
PC, o script preenche `STEAM_PC` no `docker/.env` com a pasta `~/.local/share/Steam/steamapps`.
O container usa os mesmos arquivos como mais uma biblioteca da Steam (`/mnt/games/SteamPC`):
os jogos aparecem instalados no AllGames sem baixar de novo. **Não abra as duas Steams ao mesmo
tempo**, porque as duas mexeriam nos mesmos arquivos. Para outra biblioteca (outro disco), aponte
`STEAM_PC` para a pasta `steamapps` dela e rode `docker compose up -d`.

Pastas especiais dentro de `ROMS`:

- `bios/`: BIOS dos consoles, como no ArkOS (`scph5501.bin` do PS1, `pcsx2/bios/` do PS2...).
- `bios/switch/`: `prod.keys`, `title.keys` e a pasta `firmware` do **seu** Switch. O AllGames
  instala no Eden sozinho.
- `bios/xbox/`: `mcpx_1.0.bin`, a BIOS e o `xbox_hdd.qcow2` do **seu** Xbox. O AllGames configura
  o xemu sozinho.
- `ports/`: onde o PortMaster instala os ports.

## Usando

- **Portal:** app **AllGames** no Moonlight. Tudo se faz por ali: jogar, instalar, desinstalar,
  ver downloads e o espaço em disco.
- **Área de trabalho:** app **Desktop** no Moonlight ou a página da porta 8483 (para entrar nas
  lojas ou configurar algo à mão).
- **Comandos do AllGames dentro do container:**

```bash
docker exec -it -u steamheadless allgames allgames doutor        # confere se está tudo certo
docker exec -it -u steamheadless allgames allgames roms          # ROMs encontradas por console
docker exec -it -u steamheadless allgames allgames portmaster    # ports que rodam no PC
```

## Atualizar, parar e ligar

```bash
cd ~/Emulador-allgames && git pull
cd docker && docker compose up -d --build     # NVIDIA: -f docker-compose.yml -f docker-compose.nvidia.yml
docker compose stop                            # para
docker compose start                           # liga de novo
```

O container liga sozinho quando o PC liga (`restart: unless-stopped`). Para deixar o PC sempre
disponível (sem suspender, acordando pela rede), veja [MODO-SERVIDOR.md](MODO-SERVIDOR.md).

## Fora de casa

Instale o **Tailscale no PC** (fora do container, `./scripts/instalar-tailscale.sh`) e no
celular. Como o container usa a rede do PC, o Moonlight alcança o Sunshine pelo IP do Tailscale.
Veja [CELULAR.md](CELULAR.md).

## Se algo não funcionar

| Sintoma | O que fazer |
|---|---|
| Página 8483 não abre | `docker compose logs -f` e confira se o container está ligado (`docker ps`) |
| Moonlight não acha o PC | termine a primeira configuração na porta 8483; confira se o Sunshine do PC (fora do Docker) está desligado |
| Tela preta ou sem aceleração | confira `GPU=` no `docker/.env` (`ls /dev/dri`; em PCs com duas placas a dedicada costuma ser `renderD129`). NVIDIA: use também o `docker-compose.nvidia.yml` |
| Controle não responde | o compose precisa passar `/dev/uinput` e `/dev/uhid` (já vem assim) |
| Emulador "faltando" no portal | veja `preparar.log` (comando acima). Para tentar de novo: `docker exec -u steamheadless allgames allgames preparar` |

Mais em [PROBLEMAS.md](PROBLEMAS.md).

## Sem Docker

Também dá para instalar tudo direto no Pop!\_OS, como antes: `scripts/instalar-host.sh`,
`scripts/instalar-lojas.sh` e `scripts/instalar-portmaster.sh` (veja o [README](../README.md)).
