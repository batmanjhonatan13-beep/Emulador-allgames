# Star Fox 64 — Starship (HarbourMasters).
# Na primeira execução o jogo extrai os recursos da ROM ao lado da AppImage.

instalar() { harbourmasters_instalar HarbourMasters/Starship 'linux.*\.zip$|\.appimage$'; }
executar() { harbourmasters_executar '*.appimage'; }
