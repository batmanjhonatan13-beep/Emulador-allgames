# Super Mario 64 — port sm64ex, compilado a partir do código-fonte.
# A compilação extrai texturas/sons da sua ROM (baserom.us.z64).

instalar() {
  precisa_apt build-essential bsdmainutils git python3 libglew-dev libsdl2-dev
  clonar https://github.com/sm64pc/sm64ex "$JOGO_DIR/src"
  cp "$ORIGINAL" "$JOGO_DIR/src/baserom.us.z64"
  make -C "$JOGO_DIR/src" -j"$(nproc)" VERSION=us BETTERCAMERA=1 EXTERNAL_DATA=1
}

executar() {
  cd "$JOGO_DIR/src/build/us_pc"
  exec ./sm64.us.f3dex2e --fullscreen --savepath "$JOGO_DIR"
}
