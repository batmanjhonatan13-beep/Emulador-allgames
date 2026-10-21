#!/usr/bin/env bash
# shellcheck disable=SC2154  # target_uid, target_gid e user_home vêm do steam-headless-init
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
