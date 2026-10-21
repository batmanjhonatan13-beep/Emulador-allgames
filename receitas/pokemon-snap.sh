# Pokémon Snap — Snap64Recomp: port nativo para PC por recompilação estática
# (N64: Recompiled + RT64). Precisa de Vulkan. O programa fica em
# $JOGO_DIR/programa, procura a ROM como pokemonsnap.z64 ao lado do executável
# e grava os saves em programa/saves/, no PC.

instalar() {
  precisa_apt libsdl2-2.0-0 libvulkan1
  if apt-cache show libgtk-3-0t64 &>/dev/null; then precisa_apt libgtk-3-0t64; else precisa_apt libgtk-3-0; fi

  # Cada versão vem numa pasta com outro nome; o conteúdo vai sempre para
  # programa/, assim saves/ e o cache de shaders continuam no mesmo lugar.
  local novo="${JOGO_DIR:?}/.novo" conteudo
  rm -rf "$novo"
  baixar_release JackandBeans/Snap64Recomp 'linux-x86_64\.tar\.(gz|xz)$' "$novo"
  conteudo=$novo
  if [[ $(find "$novo" -mindepth 1 -maxdepth 1 | wc -l) == 1 ]]; then
    conteudo=$(find "$novo" -mindepth 1 -maxdepth 1 -type d)
  fi
  mkdir -p "$JOGO_DIR/programa"
  cp -a "${conteudo:-$novo}/." "$JOGO_DIR/programa/"
  rm -rf "$novo"

  local programa
  programa=$(achar_executavel "$JOGO_DIR/programa" '*snap*')
  [[ -n $programa ]] || falha "não achei o executável do Snap64Recomp em $JOGO_DIR/programa"
  cp -u "$ORIGINAL" "$(dirname "$programa")/pokemonsnap.z64"
}

executar() {
  local programa
  programa=$(achar_executavel "$JOGO_DIR/programa" '*snap*')
  [[ -n $programa ]] || falha "Snap64Recomp não encontrado; rode: allgames instalar $JOGO_ID"
  cd "$(dirname "$programa")"
  exec "$programa"
}
