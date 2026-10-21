# Resident Evil 4 (2014, Ultimate HD) da sua conta Steam, rodando pelo Proton.
# Os saves ficam no PC (pasta da Steam) e na nuvem da Steam.

APPID=254700

instalar() {
  local steam=(steam)
  command -v steam >/dev/null || {
    precisa_flatpak com.valvesoftware.Steam
    steam=(flatpak run com.valvesoftware.Steam)
  }
  msg "Abrindo a instalação na Steam: entre na sua conta e confirme o download do Resident Evil 4"
  "${steam[@]}" "steam://install/$APPID" &
  disown
}

executar() {
  if command -v steam >/dev/null; then
    exec steam -silent "steam://rungameid/$APPID"
  fi
  exec flatpak run com.valvesoftware.Steam -silent "steam://rungameid/$APPID"
}
