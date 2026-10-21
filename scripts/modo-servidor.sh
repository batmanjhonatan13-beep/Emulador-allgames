#!/usr/bin/env bash
# Deixa o PC pronto para ficar ligado como servidor de jogos da casa:
#  - não suspende nem hiberna sozinho (senão o celular perde a conexão);
#  - liga o Wake-on-LAN na placa de rede com cabo (o Moonlight acorda o PC);
#  - liga o login automático, quando o gerenciador de login permite (GDM);
#  - desliga o bloqueio de tela no GNOME (no COSMIC, mostra o que ajustar).
# Para desfazer: scripts/modo-servidor.sh --desfazer
set -euo pipefail

msg() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
aviso() { printf '\033[1;33m !\033[0m %s\n' "$*"; }
falha() { printf '\033[1;31mERRO:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -ne 0 ]] || falha "rode como seu usuário normal; o script pede sudo quando precisa"
ALVOS_DE_SONO=(sleep.target suspend.target hibernate.target hybrid-sleep.target)
GDM_CONF=/etc/gdm3/custom.conf

gdm_autologin() { # <true|false>
  sudo python3 - "$GDM_CONF" "$USER" "$1" <<'EOF'
import configparser, sys
arquivo, usuario, ligar = sys.argv[1], sys.argv[2], sys.argv[3] == "true"
conf = configparser.ConfigParser(strict=False, interpolation=None)
conf.optionxform = str
conf.read(arquivo)
if not conf.has_section("daemon"):
    conf.add_section("daemon")
conf["daemon"]["AutomaticLoginEnable"] = "true" if ligar else "false"
if ligar:
    conf["daemon"]["AutomaticLogin"] = usuario
with open(arquivo, "w") as f:
    conf.write(f)
EOF
}

if [[ ${1:-} == --desfazer ]]; then
  msg "Voltando a suspender normalmente"
  sudo systemctl unmask "${ALVOS_DE_SONO[@]}"
  if [[ -f $GDM_CONF ]]; then
    msg "Desligando o login automático do GDM"
    gdm_autologin false
  fi
  if command -v gsettings >/dev/null; then
    gsettings reset org.gnome.desktop.session idle-delay || true
    gsettings reset org.gnome.desktop.screensaver lock-enabled || true
  fi
  msg "Pronto."
  exit 0
fi

# --- Sem suspensão --------------------------------------------------------------
msg "Impedindo o PC de suspender ou hibernar sozinho"
sudo systemctl mask "${ALVOS_DE_SONO[@]}"

# --- Wake-on-LAN ---------------------------------------------------------------
mac=""
if command -v nmcli >/dev/null; then
  while IFS=: read -r nome tipo dispositivo; do
    [[ $tipo == 802-3-ethernet ]] || continue
    msg "Ligando o Wake-on-LAN na conexão \"$nome\""
    sudo nmcli connection modify "$nome" 802-3-ethernet.wake-on-lan magic
    [[ -n $dispositivo && -r /sys/class/net/$dispositivo/address ]] && mac=$(cat "/sys/class/net/$dispositivo/address")
  done < <(nmcli -t -f NAME,TYPE,DEVICE connection show)
fi
[[ -n $mac ]] || aviso "nenhuma conexão por cabo encontrada: o Wake-on-LAN só funciona com cabo de rede"

# --- Login automático --------------------------------------------------------------
if systemctl is-enabled gdm3 &>/dev/null || systemctl is-enabled gdm &>/dev/null; then
  msg "Ligando o login automático do GDM para $USER"
  gdm_autologin true
else
  aviso "o login automático não foi ligado: no COSMIC (Pop!_OS 24.04), ligue em Configurações → Usuários, se a opção existir na sua versão, ou deixe a sessão aberta com o bloqueio de tela desligado"
fi

# --- Tela -------------------------------------------------------------------------
if [[ ${XDG_CURRENT_DESKTOP:-} == *GNOME* ]] && command -v gsettings >/dev/null; then
  msg "Desligando o apagar/bloquear automático da tela (GNOME)"
  gsettings set org.gnome.desktop.session idle-delay 0
  gsettings set org.gnome.desktop.screensaver lock-enabled false
else
  aviso "nas configurações de energia e tela, desligue o bloqueio automático e o apagar da tela"
fi

# --- Sunshine ---------------------------------------------------------------------
if ! systemctl --user is-enabled app-dev.lizardbyte.app.Sunshine &>/dev/null &&
  ! systemctl --user is-enabled sunshine &>/dev/null; then
  aviso "o Sunshine não está ligado com a sessão; rode scripts/instalar-host.sh"
fi

ip=$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p')
cat <<EOF

Pronto! O PC fica disponível para o celular enquanto estiver ligado.

  IP do PC na rede de casa: ${ip:-desconhecido}  (adicione no Moonlight com "+" se não aparecer)
  Wake-on-LAN: ${mac:-sem cabo de rede}

Para o Moonlight conseguir ligar o PC desligado, ative também "Wake on LAN"
(ou "Power On by PCI-E") na BIOS/UEFI da placa-mãe. Com o PC desligado, no
Moonlight mantenha o dedo sobre o PC e escolha "Enviar Wake-on-LAN".
EOF
