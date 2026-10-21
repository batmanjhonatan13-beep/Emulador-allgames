# Modelo de receita. Copie para receitas/<id>.sh, adicione o [[jogo]] em
# catalogo/jogos.toml e preencha as duas funções. Veja docs/ADICIONAR-JOGOS.md.
#
# Variáveis disponíveis: JOGO_ID, JOGO_DIR, ORIGINAIS_DIR, ORIGINAL
# Funções disponíveis (receitas/_lib.sh): precisa_apt, precisa_flatpak, clonar,
#   baixar_release, achar, achar_original, rodar_appimage, msg, falha

# Baixa/compila o jogo dentro de $JOGO_DIR. Pode ser executada de novo para atualizar.
instalar() {
  precisa_apt build-essential cmake git libsdl2-dev
  clonar https://github.com/DONO/PROJETO "$JOGO_DIR/src"
  cmake -S "$JOGO_DIR/src" -B "$JOGO_DIR/src/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$JOGO_DIR/src/build" -j"$(nproc)"
}

# Abre o jogo em tela cheia. Use `exec` para o Sunshine conseguir encerrá-lo
# quando você sair do jogo no celular.
executar() {
  cd "$JOGO_DIR/src/build"
  exec ./executavel
}
