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

# --- Configuração -----------------------------------------------------------------
cd "$REPO/docker"
if [[ ! -f .env ]]; then
  render=$(find /dev/dri -name 'renderD*' 2>/dev/null | sort | tail -n1)
  sed -e "s|/home/SEU_USUARIO|$HOME|g" -e "s|^PUID=.*|PUID=$(id -u)|" -e "s|^PGID=.*|PGID=$(id -g)|" \
    -e "s|^GPU=.*|GPU=${render:-/dev/dri/renderD128}|" .env.exemplo >.env
  msg "Configuração criada em docker/.env (confira as pastas)"
fi
set -a
# shellcheck disable=SC1091
. ./.env
set +a
mkdir -p "$DADOS"/{home,estado,journal} "$JOGOS" "$ROMS"

msg "Construindo e ligando o container (a primeira vez demora)"
"${DOCKER[@]}" compose "${compose[@]}" up -d --build

ip=$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p')
cat <<FIM

Pronto! O AllGames está ligado no container "allgames".

 1. Abra http://${ip:-IP-DO-PC}:8483 (no PC ou no celular) e crie a senha da
    primeira configuração. Isso libera o Sunshine.
 2. Entre na Steam e no Heroic pela área de trabalho do container (a mesma
    página da porta 8483 mostra a tela) uma vez.
 3. No celular, no Moonlight, adicione o PC e pareie; abra "AllGames".
 4. ROMs: copie para $ROMS/<console> (snes, psx, ps2, switch...).

Na primeira vez o container baixa os emuladores (alguns GB). Acompanhe com:
  ${DOCKER[*]} exec allgames tail -f /home/steamheadless/AllGames/logs/preparar.log
FIM
