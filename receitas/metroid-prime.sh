# Metroid Prime — a descompilação (primedecomp/prime) só reconstrói o binário
# original, sem port para PC, então o jogo roda no emulador Dolphin.

APP=org.DolphinEmu.dolphin-emu

instalar() { precisa_flatpak "$APP"; }

executar() {
  exec flatpak run --filesystem="$ORIGINAIS_DIR:ro" "$APP" \
    --batch --config=Dolphin.Display.Fullscreen=True --exec="$ORIGINAL"
}
