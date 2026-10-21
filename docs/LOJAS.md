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
- **Instalar (Epic):** o AllGames baixa pelo **legendary**, o mesmo motor que o Heroic usa, com a
  mesma conta (é só ter entrado na Epic pelo Heroic). Antes de começar ele confere se o jogo cabe
  no disco, e o progresso aparece na aba **Downloads**, com pausa. O jogo instalado aparece no
  Heroic também. O legendary vem na imagem Docker; sem Docker, o `scripts/instalar-lojas.sh`
  instala.
- **Instalar (GOG e Amazon):** o Heroic abre e pergunta se quer instalar. Confirme na tela.
- **Desinstalar:** jogos da Epic são desinstalados direto pelo legendary. Nos de GOG e Amazon o
  Heroic abre: escolha o jogo e use Desinstalar.

Jogos sem login não aparecem até você entrar na conta no Heroic.

## Downloads e espaço em disco

A aba **Downloads** do portal mostra:

- **Espaço em disco:** quanto sobra em cada disco usado pela Steam, pela Epic, pelas ROMs e pelo
  AllGames (um cartão por disco físico).
- **Cada download:** porcentagem, quanto já veio, velocidade e tempo restante. Quando o jogo
  **não cabe** no espaço livre, aparece o aviso em amarelo ("Não cabe: faltam 165 GB e o disco tem
  20 GB livres"). A aba ganha um número quando há downloads em andamento, e as capas dos jogos
  baixando mostram "Baixando 37%".

Exemplo: você mandou baixar o God of War Ragnarök na Steam, mas o disco está quase cheio. A aba
mostra o download, a porcentagem parada e o aviso de que não cabe. Libere espaço (ou mude a
biblioteca da Steam para outro disco) e ele continua de onde parou.

**Pausar e continuar:**

- **Epic:** botões **Pausar**, **Continuar** e **Parar** no próprio portal. Pausado, o download
  continua de onde parou, mesmo depois de reiniciar o PC.
- **Steam:** a Steam não deixa outro programa pausar os downloads dela, então o portal mostra o
  progresso e o botão **Abrir downloads da Steam** abre a tela de downloads dela, onde dá para
  pausar e retomar (pela tela do celular mesmo).
- **GOG e Amazon:** o progresso aparece dentro do Heroic.

**Baixar enquanto joga outro jogo:** os downloads da Epic rodam separados do jogo e continuam. Na
Steam, ligue **Configurações → Downloads → "Permitir downloads durante o jogo"**; sem isso a Steam
pausa os downloads quando um jogo abre.

**Onde os jogos ficam:** no Docker, na pasta `JOGOS` do `docker/.env` (`GameLibrary/Steam` e
`Epic`). Sem Docker, nas bibliotecas da Steam e, para a Epic, em `~/Games/Heroic` ou na pasta que
você escolher:

```toml
# ~/AllGames/config.toml
[epic]
pasta = "/mnt/hd-grande/Epic"
```

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
