# AllGames: o serviço inteiro numa imagem.
#
# Base: steam-headless 2.x (Fedora, systemd, KDE Plasma em Wayland), que já traz
# a Steam, o Sunshine (Moonlight) com tela virtual que se ajusta ao celular,
# GPU NVIDIA/AMD/Intel, áudio, Flatpak e uma interface web na porta 8483.
# Por cima entram o AllGames (portal, catálogo, ROMs, downloads), o PortMaster
# e o legendary (Epic). Os emuladores e o Heroic são instalados na primeira vez
# que o container liga (ficam no volume da home, não precisam ser baixados de novo).
ARG BASE=josh5/steam-headless:2.44.20261019.1
FROM ${BASE}

# Bibliotecas que os ports do PortMaster usam e o pip para o legendary.
RUN dnf install -y --setopt=install_weak_deps=False \
        python3-pip SDL2_mixer SDL2_image SDL2_ttf squashfuse unzip \
    && dnf clean all

# legendary: downloads da Epic com progresso, pausa e retomada (mesma conta do Heroic).
RUN pip3 install --no-cache-dir --prefix /usr/local legendary-gl

# PortMaster: os ports do R36S que rodam em PC. Fica em /opt/tools/PortMaster e
# instala os ports em /roms/ports, os caminhos que ele mesmo procura.
RUN mkdir -p /opt/tools /roms \
    && curl -fsSL -o /tmp/PortMaster.zip \
        https://github.com/PortsMaster/PortMaster-GUI/releases/latest/download/PortMaster.zip \
    && unzip -q /tmp/PortMaster.zip -d /opt/tools \
    && rm -f /tmp/PortMaster.zip \
    && chown -R 1000:1000 /opt/tools/PortMaster

COPY . /opt/allgames
RUN ln -sf /opt/allgames/bin/allgames /usr/local/bin/allgames \
    && install -m 0644 /opt/allgames/docker/allgames-apps.service /opt/allgames/docker/allgames-preparar.service \
        /usr/lib/systemd/system/ \
    && install -m 0755 /opt/allgames/docker/20-allgames.sh /usr/local/sh-init.d/20-allgames.sh \
    && systemctl enable allgames-apps.service allgames-preparar.service
