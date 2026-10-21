#!/usr/bin/env bash
# Prepara o PC (Pop!_OS ou outro Ubuntu) para transmitir jogos ao celular:
# instala o Sunshine, libera captura de tela e controles virtuais, liga o
# serviço e deixa o comando `allgames` disponível.
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
msg() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
falha() { printf '\033[1;31mERRO:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -ne 0 ]] || falha "rode como seu usuário normal; o script pede sudo quando precisa"
# shellcheck disable=SC1091
. /etc/os-release
[[ " ${ID} ${ID_LIKE:-} " == *" ubuntu "* ]] || falha "este script é para Pop!_OS/Ubuntu (encontrei: ${PRETTY_NAME})"
ARQ=$(dpkg --print-architecture)

# --- Dependências -----------------------------------------------------------
msg "Instalando dependências"
pacotes=(curl git python3 flatpak unzip vainfo)
if apt-cache show libfuse2t64 &>/dev/null; then pacotes+=(libfuse2t64); else pacotes+=(libfuse2); fi
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || pacotes+=(python3-tomli)
sudo apt-get update
sudo apt-get install -y "${pacotes[@]}"

# --- Sunshine ---------------------------------------------------------------
if command -v sunshine >/dev/null; then
  msg "Sunshine já instalado: $(command -v sunshine)"
else
  msg "Procurando o Sunshine para ${PRETTY_NAME} (${ARQ})"
  url=$(curl -fsSL https://api.github.com/repos/LizardByte/Sunshine/releases/latest | python3 -c '
import json, re, sys
padrao = re.compile(r"^sunshine_.*\+ubuntu" + re.escape(sys.argv[1]) + "_" + sys.argv[2] + r"\.deb$")
for a in json.load(sys.stdin)["assets"]:
    if padrao.search(a["name"]):
        print(a["browser_download_url"])
        break
' "$VERSION_ID" "$ARQ") || falha "não consegui consultar as releases do Sunshine no GitHub"
  [[ -n $url ]] || falha "não há .deb do Sunshine para Ubuntu ${VERSION_ID}; baixe manualmente em https://github.com/LizardByte/Sunshine/releases"
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  msg "Baixando ${url##*/}"
  curl -fL --progress-bar -o "$tmp/${url##*/}" "$url"
  sudo apt-get install -y "$tmp/${url##*/}"
fi

# Captura KMS: necessária para capturar a tela no Wayland (COSMIC/GNOME).
binario=$(readlink -f "$(command -v sunshine)")
msg "Liberando captura de tela (KMS) para $binario"
sudo setcap cap_sys_admin+p "$binario"

# --- Controles virtuais (uinput) --------------------------------------------
msg "Liberando controles virtuais (uinput)"
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf >/dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=misc
if [[ ! -w /dev/uinput ]]; then
  sudo usermod -aG input "$USER"
  precisa_relogar=1
fi

# --- Serviço ----------------------------------------------------------------
msg "Ligando o Sunshine junto com a sua sessão"
systemctl --user daemon-reload
systemctl --user enable --now app-dev.lizardbyte.app.Sunshine 2>/dev/null ||
  systemctl --user enable --now sunshine

# --- AllGames ---------------------------------------------------------------
mkdir -p "$HOME/AllGames/originais" "$HOME/.local/bin"
ln -sf "$REPO/bin/allgames" "$HOME/.local/bin/allgames"
msg "Publicando o portal AllGames (tela com as capas) no Sunshine"
"$REPO/bin/allgames" sincronizar

cat <<EOF

$(printf '\033[1;32m')Pronto!$(printf '\033[0m') Próximos passos:

 1. No PC, abra https://localhost:47990 e crie usuário e senha do Sunshine
    (o navegador vai reclamar do certificado; pode continuar).
 2. No celular, instale o Moonlight (Play Store, F-Droid ou App Store).
    Na mesma rede Wi-Fi o PC aparece sozinho; toque nele e digite o PIN
    mostrado em https://localhost:47990/pin
 3. Copie os arquivos dos seus jogos para ~/AllGames/originais (o nome não
    importa para os Pokémon: eles são reconhecidos pelo conteúdo) e rode:
      allgames verificar
      allgames instalar pokemon-emerald
 4. No Moonlight, abra "AllGames": é a tela com as capas, estilo Game Pass.
 5. Para jogar fora de casa: scripts/instalar-tailscale.sh
 6. Confira tudo com: allgames doutor
EOF
if [[ ${precisa_relogar:-0} == 1 ]]; then
  echo
  echo " ! Você foi adicionado ao grupo 'input'. Saia da sessão e entre de novo."
fi
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  echo " ! ~/.local/bin não está no PATH; abra um terminal novo ou use $REPO/bin/allgames"
fi
