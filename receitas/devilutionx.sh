# Diablo — DevilutionX (Flathub). Sem o DIABDAT.MPQ roda a demo que vem junto.

APP=org.diasurgical.DevilutionX
DADOS="$HOME/.var/app/$APP/data/diasurgical/devilution"

instalar() {
  precisa_flatpak "$APP"
  mkdir -p "$DADOS"
  # O Flatpak não enxerga links para fora da sandbox, então os MPQs são copiados.
  local nome arquivo
  for nome in DIABDAT.MPQ hellfire.mpq hfmonk.mpq hfmusic.mpq hfvoice.mpq; do
    arquivo=$(achar_original "$nome")
    [[ -n $arquivo ]] && cp -u "$arquivo" "$DADOS/$nome"
  done
  return 0
}

executar() { exec flatpak run "$APP"; }
