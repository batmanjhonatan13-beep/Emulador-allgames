#!/usr/bin/env bash
# shellcheck disable=SC2154  # user_home vem do steam-headless-init
# 80-allgames-steam-do-pc.sh: carregado pelo steam-headless-init (como root) a cada vez
# que o container liga, depois de a imagem configurar a biblioteca da Steam e antes de a
# Steam abrir. Se a Steam instalada direto no Pop!_OS foi ligada ao container (STEAM_PC
# no docker/.env), os jogos que ela já baixou viram uma biblioteca da Steam do container:
# aparecem instalados, sem baixar de novo.

if compgen -G "/mnt/games/SteamPC/steamapps/appmanifest_*.acf" >/dev/null; then
    if /usr/sbin/runuser -u steamheadless -- /usr/bin/env HOME="${user_home}" \
        /usr/local/bin/allgames lojas --registrar-steam /mnt/games/SteamPC; then
        log "AllGames: jogos da Steam do PC disponíveis em /mnt/games/SteamPC."
    else
        log "AllGames: WARNING: não deu para registrar os jogos da Steam do PC."
    fi
fi
