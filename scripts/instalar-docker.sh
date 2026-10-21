#!/usr/bin/env bash
# Instala o AllGames como um container Docker no Pop!_OS: o host só precisa do
# Docker e do driver da placa de vídeo. Steam, Sunshine, emuladores, Heroic,
# PortMaster e o portal ficam todos dentro do container.
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
msg() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
aviso() { printf '\033[1;33m !\033[0m %s\n' "$*"; }
falha() { printf '\033[1;31mERRO:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -ne 0 ]] || falha "rode como seu usuário normal; o script pede sudo quando precisa"

# --- Docker -----------------------------------------------------------------------
if ! command -v docker >/dev/null; then
  msg "Instalando o Docker"
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-v2
elif ! docker compose version >/dev/null 2>&1; then
  # Docker já instalado sem o plugin do compose (comum com o pacote docker.io).
  msg "Instalando o Docker Compose"
  sudo apt-get update
  if dpkg -s docker-ce >/dev/null 2>&1; then
    sudo apt-get install -y docker-compose-plugin # Docker do repositório oficial
  else
    sudo apt-get install -y docker-compose-v2
  fi
fi
if ! id -nG "$USER" | grep -qw docker; then
  sudo usermod -aG docker "$USER"
  aviso "você entrou no grupo docker: este script usa sudo agora; depois de sair e entrar na sessão, não precisa"
fi
DOCKER=(docker)
docker info >/dev/null 2>&1 || DOCKER=(sudo docker)

# --- NVIDIA -----------------------------------------------------------------------
compose=(-f docker-compose.yml)
if command -v nvidia-smi >/dev/null; then
  if ! command -v nvidia-ctk >/dev/null; then
    msg "Instalando o NVIDIA Container Toolkit (para a placa funcionar dentro do container)"
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey |
      sudo gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' |
      sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
  fi
  compose+=(-f docker-compose.nvidia.yml)
fi

# --- Sunshine do host -------------------------------------------------------------
# O container usa as mesmas portas; o Sunshine instalado direto no PC precisa parar.
for servico in app-dev.lizardbyte.app.Sunshine sunshine; do
  if systemctl --user is-enabled "$servico" &>/dev/null; then
    msg "Desligando o Sunshine instalado no PC (o do container assume)"
    systemctl --user disable --now "$servico" || true
  fi
done

# --- Entrada virtual ----------------------------------------------------------------
# O mouse, o teclado e os controles virtuais do Sunshine do container ficam só no container
# (sem isto, tocar na tela do celular mexe o mouse do PC).
regra=/etc/udev/rules.d/60-allgames-entrada-virtual.rules
if ! cmp -s "$REPO/docker/60-allgames-entrada-virtual.rules" "$regra"; then
  msg "Separando o mouse e os controles do celular dos do PC"
  sudo install -m 0644 "$REPO/docker/60-allgames-entrada-virtual.rules" "$regra"
  sudo udevadm control --reload
  sudo udevadm trigger --subsystem-match=input --action=change
fi

# --- Configuração -----------------------------------------------------------------
cd "$REPO/docker"
if [[ ! -f .env ]]; then
  render=$(find /dev/dri -name 'renderD*' 2>/dev/null | sort | tail -n1)
  steam_pc=""
  [[ -d "$HOME/.local/share/Steam/steamapps" ]] && steam_pc="$HOME/.local/share/Steam/steamapps"
  sed -e "s|/home/SEU_USUARIO|$HOME|g" -e "s|^PUID=.*|PUID=$(id -u)|" -e "s|^PGID=.*|PGID=$(id -g)|" \
    -e "s|^GPU=.*|GPU=${render:-/dev/dri/renderD128}|" -e "s|^STEAM_PC=.*|STEAM_PC=$steam_pc|" .env.exemplo >.env
  msg "Configuração criada em docker/.env (confira as pastas)"
fi
set -a
# shellcheck disable=SC1091
. ./.env
set +a
# As pastas são criadas aqui, com o seu usuário (o Docker criaria como root).
mkdir -p "$DADOS"/{home,estado,journal,sem-steam-do-pc} "$JOGOS/SteamPC/steamapps" "$ROMS"

msg "Construindo e ligando o container (a primeira vez demora)"
"${DOCKER[@]}" compose "${compose[@]}" up -d --build

ip=$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p')
cat <<FIM

Pronto! O AllGames está ligado no container "allgames".

 1. Abra https://${ip:-IP-DO-PC}:8483 (no PC ou no celular), aceite o aviso de
    certificado e entre com o usuário steamheadless e a senha temporária:
      ${DOCKER[*]} logs allgames 2>&1 | grep 'Temporary password'
    Crie a sua senha. Isso libera o Sunshine.
 2. Entre na Steam e no Heroic pela área de trabalho do container (a mesma
    página da porta 8483 mostra a tela) uma vez.
 3. No celular, no Moonlight, adicione o PC (se não aparecer sozinho, toque
    em + e digite ${ip:-o IP do PC}) e pareie; abra "AllGames".
 4. ROMs: copie para $ROMS/<console> (snes, psx, ps2, switch...).

Na primeira vez o container baixa os emuladores (alguns GB). Acompanhe com:
  ${DOCKER[*]} exec allgames tail -f /home/steamheadless/AllGames/logs/preparar.log
FIM
