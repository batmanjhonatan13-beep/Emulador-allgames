# Funções compartilhadas pelas receitas. Carregado pelo `allgames` antes de
# receitas/<id>.sh, com estas variáveis já definidas:
#   JOGO_ID        id do jogo no catálogo
#   JOGO_DIR       pasta de instalação do jogo (~/AllGames/jogos/<id>)
#   ORIGINAIS_DIR  pasta com os arquivos originais (~/AllGames/originais)
#   ORIGINAL       caminho do primeiro arquivo original encontrado (pode ser vazio)

msg() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
falha() { printf '\033[1;31mERRO:\033[0m %s\n' "$*" >&2; exit 1; }

# precisa_apt <pacote>... : instala com apt só o que ainda não estiver instalado.
precisa_apt() {
  local faltando=() p
  for p in "$@"; do
    dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q 'install ok installed' || faltando+=("$p")
  done
  ((${#faltando[@]})) || return 0
  msg "Instalando pacotes do sistema: ${faltando[*]}"
  sudo apt-get install -y "${faltando[@]}"
}

# precisa_flatpak <app-id> : instala o app do Flathub (por usuário) se faltar.
precisa_flatpak() {
  command -v flatpak >/dev/null || precisa_apt flatpak
  flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
  flatpak info "$1" &>/dev/null || flatpak install --user -y --noninteractive flathub "$1"
}

# clonar <url> <destino> : clona com submódulos, ou atualiza se já existir.
clonar() {
  if [[ -d "$2/.git" ]]; then
    msg "Atualizando $(basename "$2")"
    git -C "$2" pull --ff-only
  else
    msg "Clonando $1"
    git clone --recursive "$1" "$2"
  fi
  git -C "$2" submodule update --init --recursive
}

# baixar_release <dono/repo> <regex> <destino> [tag]
# Baixa o primeiro arquivo da release (a mais recente, ou a da tag) cujo nome
# bate com a regex (sem diferenciar maiúsculas) e extrai zip/tar no destino.
baixar_release() {
  local repo=$1 padrao=$2 destino=$3 tag=${4:-}
  local api="https://api.github.com/repos/$repo/releases/latest"
  [[ -n $tag ]] && api="https://api.github.com/repos/$repo/releases/tags/$tag"
  local auth=()
  [[ -n ${GITHUB_TOKEN:-} ]] && auth=(-H "Authorization: Bearer $GITHUB_TOKEN")

  local url
  url=$(curl -fsSL "${auth[@]}" "$api" | python3 -c '
import json, re, sys
padrao = re.compile(sys.argv[1], re.I)
assets = json.load(sys.stdin).get("assets", [])
for a in assets:
    if padrao.search(a["name"]):
        print(a["browser_download_url"])
        break
else:
    print("Arquivos disponíveis: " + ", ".join(a["name"] for a in assets), file=sys.stderr)
' "$padrao") || falha "não consegui consultar as releases de $repo"
  [[ -n $url ]] || falha "nenhum arquivo da release de $repo bate com /$padrao/"

  mkdir -p "$destino"
  local arquivo="$destino/${url##*/}"
  msg "Baixando ${url##*/}"
  curl -fL --progress-bar -o "$arquivo" "$url"
  case "${arquivo,,}" in
    *.zip) precisa_apt unzip; unzip -oq "$arquivo" -d "$destino"; rm -f "$arquivo" ;;
    *.tar.gz | *.tgz | *.tar.xz | *.tar.bz2 | *.tar.zst) tar -xf "$arquivo" -C "$destino"; rm -f "$arquivo" ;;
    *.appimage) chmod +x "$arquivo" ;;
  esac
}

# achar <pasta> <padrão> : primeiro arquivo cujo nome bate com o padrão (sem
# diferenciar maiúsculas).
achar() { find "$1" -type f -iname "$2" -print -quit 2>/dev/null; }

# achar_original <padrão> : arquivo original em ORIGINAIS_DIR.
achar_original() { achar "$ORIGINAIS_DIR" "$1"; }

# achar_executavel <pasta> <padrão> : primeiro executável (não biblioteca) com o nome.
achar_executavel() {
  find "$1" -type f -perm -u+x -iname "$2" ! -name '*.so' ! -name '*.so.*' -print -quit 2>/dev/null
}

# rom_local : caminho da cópia da ROM dentro de JOGO_DIR (<id>.<extensão>).
# Os emuladores gravam o save ao lado da ROM, então copiar a ROM para cá faz o
# progresso ficar em ~/AllGames/jogos/<id>, junto com o resto do jogo.
rom_local() { echo "$JOGO_DIR/$JOGO_ID.${ORIGINAL##*.}"; }

copiar_rom() {
  [[ -n $ORIGINAL ]] || falha "arquivo original não encontrado em $ORIGINAIS_DIR"
  cp -u "$ORIGINAL" "$(rom_local)"
}

# rodar_appimage <arquivo> [args...] : executa substituindo o processo atual.
# Sem a libfuse2 no sistema, a AppImage é extraída a cada execução (mais lento).
rodar_appimage() {
  [[ -n $1 && -f $1 ]] || falha "AppImage não encontrada; rode: allgames instalar $JOGO_ID"
  chmod +x "$1"
  ldconfig -p 2>/dev/null | grep -q 'libfuse\.so\.2' || export APPIMAGE_EXTRACT_AND_RUN=1
  exec "$@"
}

# --- Ports da HarbourMasters (libultraship) ---------------------------------
# Todos seguem o mesmo padrão: release com AppImage para Linux, ROM colocada ao
# lado dela e, na primeira execução, o jogo extrai os recursos da ROM (.o2r).

harbourmasters_instalar() { # <dono/repo> <regex-do-arquivo-linux>
  # Cada versão tem um nome de AppImage diferente; apaga a antiga para não abri-la.
  [[ -d $JOGO_DIR ]] && find "$JOGO_DIR" -maxdepth 2 -type f -iname '*.appimage' -delete
  baixar_release "$1" "$2" "$JOGO_DIR"
  [[ -n $ORIGINAL ]] && ln -sf "$ORIGINAL" "$JOGO_DIR/$(basename "$ORIGINAL")"
  return 0
}

harbourmasters_executar() { # <padrão-da-appimage>
  cd "$JOGO_DIR"
  # SHIP_HOME mantém saves, configurações e o .o2r gerado dentro de JOGO_DIR.
  export SHIP_HOME="$JOGO_DIR"
  rodar_appimage "$(achar "$JOGO_DIR" "$1")"
}
