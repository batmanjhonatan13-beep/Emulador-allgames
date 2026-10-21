#!/usr/bin/env bash
# shellcheck disable=SC2154  # target_uid, target_gid, user_home e user_name vêm do steam-headless-init
# 20-allgames.sh: carregado pelo steam-headless-init (como root) a cada vez que
# o container liga. A pasta de ROMs do host fica em /roms; o AllGames a enxerga
# em ~/AllGames/roms, e o PortMaster (que procura /roms/ports) também.

log "AllGames: preparando ~/AllGames e /roms."
install -d -o "${target_uid}" -g "${target_gid}" /roms /roms/bios /roms/ports "${user_home}/AllGames" "${user_home}/AllGames/logs"
if [[ ! -e "${user_home}/AllGames/roms" ]]; then
    ln -s /roms "${user_home}/AllGames/roms"
    chown -h "${target_uid}:${target_gid}" "${user_home}/AllGames/roms"
fi
chown "${target_uid}:${target_gid}" /opt/tools/PortMaster

# Segunda sessão no mesmo PC (docker-compose.yml, perfil segunda-sessao): com a rede do
# host, as portas da primeira sessão já estão em uso, então esta usa as suas.
if [[ -n "${ALLGAMES_PORTA:-}" ]]; then
    # O systemd do container não herda o ambiente do Docker: o portal lê daqui.
    echo "ALLGAMES_PORTA=${ALLGAMES_PORTA}" >>/run/steam-headless/environment
fi
# Muda (ou tira, sem valor) uma opção do sunshine.conf antes de o Sunshine abrir. Se o
# arquivo ainda não existe, começa com o que o steam-headless poria nele.
sunshine_conf="${user_home}/.config/sunshine/sunshine.conf"
sunshine_opcao() {
    /usr/sbin/runuser -u "${user_name}" -- mkdir -p "${user_home}/.config/sunshine"
    if [[ ! -s "${sunshine_conf}" ]]; then
        printf 'sunshine_name = %s\nupnp = disabled\n' "${HOSTNAME}" >"${sunshine_conf}"
    fi
    sed -i -E "/^[[:space:]]*$1[[:space:]]*=/d" "${sunshine_conf}"
    if [[ -n "${2:-}" ]]; then
        echo "$1 = $2" >>"${sunshine_conf}"
    fi
    chown "${target_uid}:${target_gid}" "${sunshine_conf}"
}
if [[ -n "${ALLGAMES_SUNSHINE_PORTA:-}" ]]; then
    log "AllGames: Sunshine desta sessão na porta ${ALLGAMES_SUNSHINE_PORTA}."
    sunshine_opcao port "${ALLGAMES_SUNSHINE_PORTA}"
fi
# TOQUE=nao no docker/.env: só o controle comanda; tocar na tela do celular não vira mouse.
if [[ "${ALLGAMES_TOQUE:-sim}" == "nao" ]]; then
    log "AllGames: toque e mouse do celular desligados (só o controle)."
    sunshine_opcao mouse disabled
    sunshine_opcao native_pen_touch disabled
else
    sunshine_opcao mouse
    sunshine_opcao native_pen_touch
fi
if [[ -n "${ALLGAMES_SUNSHINE_PORTA:-}" ]]; then
    # O painel só aceita o Sunshine em 127.0.0.1:47990. Esta sessão tem rede própria, então
    # essa porta está livre aqui dentro e é repassada para o Sunshine desta sessão.
    cat >/etc/systemd/system/allgames-sunshine-do-painel.service <<FIM
[Unit]
Description=AllGames: o painel desta sessão fala com o Sunshine dela
Before=steam-headless-shui.service

[Service]
ExecStart=/usr/sbin/socat TCP-LISTEN:47990,bind=127.0.0.1,fork,reuseaddr TCP:127.0.0.1:$((ALLGAMES_SUNSHINE_PORTA + 1))
Restart=always

[Install]
WantedBy=multi-user.target
FIM
    install -d /etc/systemd/system/multi-user.target.wants
    ln -sf /etc/systemd/system/allgames-sunshine-do-painel.service /etc/systemd/system/multi-user.target.wants/
fi
if [[ -n "${ALLGAMES_PAINEL_PORTA:-}" ]]; then
    log "AllGames: painel desta sessão na porta ${ALLGAMES_PAINEL_PORTA}."
    publico=()
    [[ -n "${ALLGAMES_IP:-}" ]] && publico=(-webrtc-public-ip "${ALLGAMES_IP}")
    install -d /etc/systemd/system/steam-headless-shui.service.d
    cat >/etc/systemd/system/steam-headless-shui.service.d/50-allgames-porta.conf <<FIM
[Service]
ExecStart=
ExecStart=/opt/steam-headless/shui/bin/shui-server -listen :${ALLGAMES_PAINEL_PORTA} -webrtc-listen :${ALLGAMES_PAINEL_PORTA} ${publico[*]}
FIM
fi
