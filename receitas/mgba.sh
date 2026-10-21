# Game Boy, Game Boy Color e Game Boy Advance no mGBA (Flathub).
# Serve para qualquer jogo do catálogo com `receita = "mgba"`. A ROM é copiada
# para a pasta do jogo e o mGBA grava o save (.sav) ao lado dela, no PC.

APP=io.mgba.mGBA

instalar() {
  precisa_flatpak "$APP"
  copiar_rom
}

executar() {
  exec flatpak run --filesystem="$JOGO_DIR" "$APP" --fullscreen "$(rom_local)"
}
