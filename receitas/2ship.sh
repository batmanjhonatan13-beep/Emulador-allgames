# Zelda: Majora's Mask — 2 Ship 2 Harkinian (HarbourMasters).
# Na primeira execução o jogo gera o mm.o2r a partir da ROM ao lado da AppImage.

instalar() { harbourmasters_instalar HarbourMasters/2ship2harkinian 'linux.*\.zip$|\.appimage$'; }
executar() { harbourmasters_executar '2ship*.appimage'; }
