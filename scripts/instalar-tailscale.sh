#!/usr/bin/env bash
# Instala o Tailscale (VPN privada) para jogar pelo celular fora de casa sem
# abrir portas no roteador. Instale o app Tailscale no celular com a mesma conta.
set -euo pipefail

msg() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }

if ! command -v tailscale >/dev/null; then
  msg "Instalando o Tailscale (script oficial de tailscale.com)"
  curl -fsSL https://tailscale.com/install.sh | sh
fi

msg "Conectando este PC à sua rede Tailscale (abra o link que aparecer)"
sudo tailscale up

ip=$(tailscale ip -4 | head -n1)
cat <<EOF

Pronto! IP do PC na rede Tailscale: $ip

No celular:
 1. Instale o app Tailscale e entre com a mesma conta.
 2. No Moonlight, toque em "+" e adicione o PC pelo IP $ip
 3. Pareie com o PIN, como em casa. Depois disso funciona no 4G/5G.
EOF
