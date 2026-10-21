#!/usr/bin/env bash
# Instala a Steam e o Heroic (Epic, GOG e Amazon) pelo Flathub, para as suas
# bibliotecas aparecerem no portal AllGames. Se a Steam já estiver instalada
# (pacote do Pop!_OS), ela é aproveitada.
set -euo pipefail

msg() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }

command -v flatpak >/dev/null || sudo apt-get install -y flatpak
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

if command -v steam >/dev/null || flatpak info com.valvesoftware.Steam &>/dev/null; then
  msg "Steam já instalada"
else
  msg "Instalando a Steam"
  flatpak install --user -y --noninteractive flathub com.valvesoftware.Steam
fi

if command -v heroic >/dev/null || flatpak info com.heroicgameslauncher.hgl &>/dev/null; then
  msg "Heroic já instalado"
else
  msg "Instalando o Heroic Games Launcher (Epic, GOG, Amazon)"
  flatpak install --user -y --noninteractive flathub com.heroicgameslauncher.hgl
fi

cat <<'FIM'

Pronto! Agora, no PC (uma vez só):

 1. Abra a Steam e entre na sua conta. Em Configurações → Compatibilidade,
    ligue "Ativar o Steam Play para todos os outros títulos" (jogos de Windows
    rodam pelo Proton).
 2. Abra o Heroic e entre nas contas Epic Games, GOG e Amazon. Jogos da Ubisoft
    comprados na Epic abrem o Ubisoft Connect sozinhos.
 3. Opcional, para ver no portal também os jogos da Steam que não estão
    instalados: crie ~/AllGames/config.toml com

      [steam]
      chave_api = "SUA_CHAVE"   # https://steamcommunity.com/dev/apikey
      steamid = "7656119..."    # o número do seu perfil (SteamID64)

 4. Confira com: allgames lojas
FIM
