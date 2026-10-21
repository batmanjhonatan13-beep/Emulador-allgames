#!/usr/bin/env bash
# Instala o PortMaster direto no Pop!_OS (no Docker ele já vem pronto), para
# pesquisar, instalar e jogar os ports do R36S pelo portal AllGames.
#
# O PortMaster procura as próprias ferramentas em /opt/tools/PortMaster e
# instala os ports em /roms/ports; /roms vira um atalho para ~/AllGames/roms.
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PACOTE=https://github.com/PortsMaster/PortMaster-GUI/releases/latest/download/PortMaster.zip
ROMS=${ALLGAMES_HOME:-$HOME/AllGames}/roms

msg() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
aviso() { printf '\033[1;33m !\033[0m %s\n' "$*"; }
falha() { printf '\033[1;31mERRO:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -ne 0 ]] || falha "rode como seu usuário normal; o script pede sudo quando precisa"

msg "Instalando as bibliotecas que os ports usam"
sudo apt-get update
sudo apt-get install -y unzip curl squashfuse libsdl2-2.0-0 libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 \
  libsdl2-ttf-2.0-0 libmodplug1

msg "Baixando o PortMaster"
temporario=$(mktemp -d)
trap 'rm -rf "$temporario"' EXIT
curl -fsSL -o "$temporario/PortMaster.zip" "$PACOTE"
sudo mkdir -p /opt/tools
sudo unzip -oq "$temporario/PortMaster.zip" -d /opt/tools
sudo chown -R "$(id -u):$(id -g)" /opt/tools/PortMaster

mkdir -p "$ROMS/ports"
if [[ -L /roms || ! -e /roms ]]; then
  sudo ln -sfn "$ROMS" /roms
  msg "/roms aponta para $ROMS"
elif [[ "$(realpath /roms)" != "$(realpath "$ROMS")" ]]; then
  aviso "/roms já existe e não é um atalho para $ROMS: os ports vão ficar em /roms/ports"
fi

"$REPO/bin/allgames" preparar --sem-emuladores

cat <<'FIM'

Pronto! No portal, abra a Biblioteca e escolha o filtro "PortMaster" (ou
pesquise pelo nome). Pelo terminal:

  allgames portmaster            # ports que rodam no PC
  allgames portmaster instalar 2048
FIM
