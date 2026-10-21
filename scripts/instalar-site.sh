#!/usr/bin/env bash
# OPCIONAL: instala o Moonlight Web (MrCreativ3001/moonlight-web-stream), um
# site que roda no PC e transmite os jogos do Sunshine para o navegador do
# celular via WebRTC — sem instalar app. O app Moonlight continua sendo a
# opção com menos atraso; use o site quando não puder instalar nada.
set -euo pipefail

DESTINO="$HOME/AllGames/site"
SERVICO=allgames-site
msg() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
falha() { printf '\033[1;31mERRO:\033[0m %s\n' "$*" >&2; exit 1; }

case "$(uname -m)" in
  x86_64) arq='x86_64|amd64' ;;
  aarch64) arq='aarch64|arm64' ;;
  *) falha "arquitetura $(uname -m) sem build pronto do Moonlight Web" ;;
esac

msg "Procurando a versão mais recente do Moonlight Web"
url=$(curl -fsSL https://api.github.com/repos/MrCreativ3001/moonlight-web-stream/releases/latest | python3 -c '
import json, re, sys
arq = re.compile(sys.argv[1], re.I)
assets = json.load(sys.stdin)["assets"]
for a in assets:
    nome = a["name"].lower()
    if "linux" in nome and arq.search(nome) and nome.endswith((".tar.gz", ".tar.xz", ".zip")):
        print(a["browser_download_url"])
        break
else:
    print("Arquivos disponíveis: " + ", ".join(a["name"] for a in assets), file=sys.stderr)
' "$arq") || falha "não consegui consultar as releases do Moonlight Web no GitHub"
[[ -n $url ]] || falha "não achei um build Linux; baixe manualmente em https://github.com/MrCreativ3001/moonlight-web-stream/releases"

mkdir -p "$DESTINO"
arquivo="$DESTINO/${url##*/}"
msg "Baixando ${url##*/}"
curl -fL --progress-bar -o "$arquivo" "$url"
case "$arquivo" in
  *.zip) unzip -oq "$arquivo" -d "$DESTINO" ;;
  *) tar -xf "$arquivo" -C "$DESTINO" ;;
esac
rm -f "$arquivo"

servidor=$(find "$DESTINO" -type f -name web-server -print -quit)
[[ -n $servidor ]] || falha "o pacote não tem o executável web-server"
chmod +x "$servidor"
pasta=$(dirname "$servidor")

if [[ ! -f "$pasta/server/config.json" ]]; then
  msg "Gerando configuração padrão"
  (cd "$pasta" && ./web-server config generate)
fi

msg "Criando o serviço $SERVICO"
mkdir -p "$HOME/.config/systemd/user"
cat >"$HOME/.config/systemd/user/$SERVICO.service" <<EOF
[Unit]
Description=AllGames - Moonlight Web (jogar pelo navegador)
After=network-online.target

[Service]
WorkingDirectory=$pasta
ExecStart=$servidor
Restart=on-failure

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now "$SERVICO"

cat <<EOF

Pronto! O site está em http://localhost:8080
 1. Abra no PC, crie o primeiro usuário (vira administrador) e adicione o
    PC "localhost". Digite o PIN mostrado no Sunshine (https://localhost:47990/pin).
 2. No celular, na mesma rede, abra http://IP-DO-PC:8080

Controle no navegador exige HTTPS. Com o Tailscale ligado (e HTTPS ativado no
painel do Tailscale), publique o site com certificado válido só para você:
    sudo tailscale serve --bg 8080
e abra no celular o endereço https://<nome-do-pc>.<sua-rede>.ts.net
EOF
