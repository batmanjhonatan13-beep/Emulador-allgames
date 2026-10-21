# Resident Evil 4 (GameCube) no Dolphin. O jogo tem dois discos: a receita
# monta uma playlist .m3u e liga a troca automática de disco do Dolphin.
# Os saves ficam no cartão de memória virtual do Dolphin, no PC.

APP=org.DolphinEmu.dolphin-emu

instalar() { precisa_flatpak "$APP"; }

executar() {
  local disco1 disco2
  disco1=$(achar_original 're4-disco1.*')
  disco2=$(achar_original 're4-disco2.*')
  [[ -n $disco1 && -n $disco2 ]] || falha "faltam re4-disco1.* e re4-disco2.* em $ORIGINAIS_DIR"
  printf '%s\n' "$disco1" "$disco2" >"$JOGO_DIR/re4.m3u"
  exec flatpak run --filesystem="$ORIGINAIS_DIR:ro" --filesystem="$JOGO_DIR:ro" "$APP" \
    --batch --config=Dolphin.Display.Fullscreen=True --config=Dolphin.Core.AutoDiscChange=True \
    --exec="$JOGO_DIR/re4.m3u"
}
