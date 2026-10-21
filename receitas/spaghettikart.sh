# Mario Kart 64 — SpaghettiKart (HarbourMasters).
# Na primeira execução o jogo extrai os recursos da ROM ao lado da AppImage.

instalar() { harbourmasters_instalar HarbourMasters/SpaghettiKart 'linux.*\.zip$|\.appimage$'; }
executar() { harbourmasters_executar '*.appimage'; }
