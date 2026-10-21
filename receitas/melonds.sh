# Nintendo DS no melonDS (Flathub). Serve para qualquer jogo do catálogo com
# `receita = "melonds"`. A ROM é copiada para a pasta do jogo e o melonDS grava
# o save (.sav) ao lado dela, no PC. Jogos de DS não precisam de BIOS (o melonDS
# usa a FreeBIOS embutida); a tela de baixo responde ao toque/mouse.

APP=net.kuribo64.melonDS

instalar() {
  precisa_flatpak "$APP"
  copiar_rom
}

executar() {
  exec flatpak run --filesystem="$JOGO_DIR" "$APP" --fullscreen "$(rom_local)"
}
