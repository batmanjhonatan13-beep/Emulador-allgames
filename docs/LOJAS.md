# Steam, Epic, GOG, Amazon, Ubisoft e Game Pass

Os jogos de PC rodam no seu Pop!\_OS (os de Windows rodam pelo **Proton/Wine**) e aparecem no
portal com capa, ao lado das ROMs. Pelo celular você joga, instala e desinstala.

```bash
./scripts/instalar-lojas.sh   # Steam e Heroic pelo Flathub (aproveita a Steam que já estiver instalada)
allgames lojas --detalhes     # o que o AllGames encontrou
```

## Steam

1. Abra a Steam no PC e entre na sua conta.
2. Em **Configurações → Compatibilidade**, ligue **"Ativar o Steam Play para todos os outros
   títulos"**. É isso que faz os jogos de Windows rodarem pelo Proton.
3. Os jogos **instalados** aparecem no portal sozinhos (a coleção "Steam").

Para ver também os jogos **comprados e não instalados** (e instalá-los pelo celular), o AllGames
precisa da lista da sua conta, que vem da Web API da Steam:

1. Gere uma chave em <https://steamcommunity.com/dev/apikey> (no campo de domínio, qualquer nome
   serve, por exemplo `allgames.local`).
2. Pegue o seu **SteamID64** (o número de 17 dígitos no endereço do seu perfil, ou em sites como
   steamid.io).
3. Crie `~/AllGames/config.toml`:

   ```toml
   [steam]
   chave_api = "SUA_CHAVE"
   steamid = "76561198000000000"
   ```

   A chave fica só no seu PC. A lista é atualizada a cada 6 horas. Se os detalhes de jogos do
   perfil forem privados, a API pode devolver a lista vazia; nesse caso, deixe "Detalhes dos jogos"
   como público nas configurações de privacidade do perfil.

No portal:

- **Jogar:** a Steam abre o jogo. O portal (e o Sunshine) acompanham o processo do jogo e voltam
  quando ele fecha.
- **Instalar / Desinstalar:** abre a janela da Steam de instalação/desinstalação no PC. Ela aparece
  na tela do celular para você confirmar.

## Epic Games, GOG e Amazon (pelo Heroic)

O [Heroic Games Launcher](https://heroicgameslauncher.com) é o launcher de Linux para essas lojas.

1. Abra o Heroic no PC e entre nas contas **Epic Games**, **GOG** e **Amazon Games**.
2. A biblioteca que o Heroic guarda aparece no portal: coleções "Epic Games", "GOG" e "Amazon
   Games".

No portal:

- **Jogar:** abre pelo Heroic, sem mostrar a janela dele. O portal acompanha o jogo pela pasta de
  instalação.
- **Instalar:** o Heroic abre e pergunta se quer instalar. Confirme na tela.
- **Desinstalar:** o Heroic abre. Escolha o jogo e use Desinstalar. O Heroic não tem um comando
  direto para isso.

Jogos sem login não aparecem até você entrar na conta no Heroic.

## Ubisoft Connect

- **Jogos da Ubisoft comprados na Steam ou na Epic** funcionam: ao abrir, o Ubisoft Connect sobe
  junto dentro do Proton/Wine e pede login na primeira vez.
- **Jogos comprados direto na Ubisoft** não têm uma loja para Linux. O caminho é instalar o
  Ubisoft Connect como jogo "não-Steam":
  - no Heroic: **Adicionar jogo → Instalador** (`UbisoftConnectInstaller.exe`); ou
  - na Steam: **Adicionar um jogo → Adicionar um jogo não-Steam**, com Proton forçado nas
    propriedades.

  Os apps adicionados no Heroic aparecem no portal (coleção "Heroic"). Instale os jogos de dentro
  do próprio Ubisoft Connect.

## EA App (Origin)

Igual à Ubisoft: jogos da EA comprados na Steam/Epic funcionam; o EA App sozinho vai como jogo
não-Steam ou "Adicionar jogo" no Heroic.

## E o Game Pass?

**Os jogos do PC Game Pass não rodam no Linux.** Eles são instalados pelo app Xbox/Microsoft Store,
que só existe no Windows, e o Proton não suporta esse sistema de instalação. Até onde sei (outubro
de 2026), continua assim. As alternativas são:

1. **Xbox Cloud Gaming:** com o **Game Pass Ultimate**, os jogos já rodam na nuvem da Microsoft.
   Abra **xbox.com/play** no navegador do celular, ou o app Xbox. Isso é exatamente "cloud gaming"
   e não precisa do PC.
2. **Comprar na Steam:** muitos jogos do Game Pass também são vendidos na Steam, e aí entram no
   AllGames normalmente.
3. **Windows no PC (dual boot):** se quiser os jogos do Game Pass rodando no seu hardware, instale
   o Windows em outra partição, com o Sunshine (ou o Apollo) para transmitir. O Moonlight do
   celular funciona igual com os dois sistemas.

## Saves

- **Steam:** na pasta da Steam no PC e na nuvem da Steam. O AllGames também copia a pasta
  `userdata/<conta>/<jogo>` antes de cada partida.
- **Heroic:** quando o Heroic sabe a pasta de saves do jogo (`save_path`), ela entra nas cópias. A
  sincronização com a nuvem da Epic/GOG é feita pelo próprio Heroic.
