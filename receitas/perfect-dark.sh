# Perfect Dark — port de fgsfdsfgs, compilado a partir do código-fonte.
# O port lê a ROM em data/pd.ntsc-final.z64 ao lado do executável.

instalar() {
  precisa_apt build-essential cmake git python3 libsdl2-dev zlib1g-dev libgl-dev
  clonar https://github.com/fgsfdsfgs/perfect_dark "$JOGO_DIR/src"
  cmake -G"Unix Makefiles" -S "$JOGO_DIR/src" -B "$JOGO_DIR/src/build"
  cmake --build "$JOGO_DIR/src/build" -j"$(nproc)"
  mkdir -p "$JOGO_DIR/src/build/data"
  ln -sf "$ORIGINAL" "$JOGO_DIR/src/build/data/pd.ntsc-final.z64"
}

executar() {
  cd "$JOGO_DIR/src/build"
  exec ./pd.x86_64
}
