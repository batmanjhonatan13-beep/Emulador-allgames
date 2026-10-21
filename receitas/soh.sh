# Zelda: Ocarina of Time — Ship of Harkinian (HarbourMasters).
# Na primeira execução o jogo gera o oot.o2r a partir da ROM; se ele pedir,
# escolha o arquivo em ~/AllGames/originais.

instalar() { harbourmasters_instalar HarbourMasters/Shipwright 'linux.*\.zip$|\.appimage$'; }
executar() { harbourmasters_executar 'soh*.appimage'; }
