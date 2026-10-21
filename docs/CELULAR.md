# Jogando pelo celular

## 1. Instale o Moonlight

- **Android:** "Moonlight Game Streaming" na Play Store, ou `com.limelight` no F-Droid.
- **iPhone/iPad:** "Moonlight Game Streaming" na App Store.

## 2. Pareie com o PC (uma vez só)

1. Celular e PC na mesma rede Wi-Fi.
2. Abra o Moonlight. O PC aparece na lista (se não aparecer, toque em **+** e digite o IP do PC,
   que aparece em `ip -4 addr` ou nas configurações de rede do Pop!\_OS).
3. Toque no PC. O Moonlight mostra um PIN de 4 dígitos.
4. No PC, abra https://localhost:47990/pin e digite o PIN.

Pronto: ao tocar no PC aparecem os jogos publicados por `allgames sincronizar`, com capa.

## 3. Configurações recomendadas no Moonlight

| Opção | Em casa (Wi-Fi 5 GHz) | Fora de casa (4G/5G) |
|---|---|---|
| Resolução | a da tela do celular, ou 1080p | 720p |
| Taxa de quadros | 60 FPS (ou 90/120 se o celular suportar) | 60 FPS |
| Taxa de bits (bitrate) | 20–40 Mbps | 5–10 Mbps |
| Codec | HEVC (H.265) ou AV1, se disponíveis | HEVC |

10 Mbps gastam cerca de 4,5 GB por hora de jogo no plano de dados.

Para o jogo renderizar direto na resolução do celular, sem bordas pretas, publique os jogos
com `allgames sincronizar --gamescope` (precisa do pacote `gamescope`: `sudo apt install gamescope`).

## 4. Controles

- **Controle Bluetooth** (Xbox, DualSense, 8BitDo) ou controle de encaixar no celular (Backbone,
  Razer Kishi): é a melhor opção. O Sunshine entrega os comandos ao jogo como um controle de Xbox.
- **Controles na tela:** no Moonlight, ative "Mostrar controles na tela" (Android) ou
  "On-Screen Controls" (iOS).
- **Sair do jogo:** feche a sessão pelo menu do Moonlight durante o jogo, ou mantenha o dedo
  sobre o jogo na lista e escolha encerrar. O Sunshine fecha o jogo no PC.

## 5. Jogar fora de casa (4G/5G)

Use o Tailscale, uma rede privada entre os seus dispositivos. Não é preciso abrir portas no
roteador, e ninguém de fora enxerga o PC.

1. No PC: `./scripts/instalar-tailscale.sh`
2. No celular: instale o app **Tailscale** e entre com a mesma conta.
3. No Moonlight, toque em **+** e adicione o PC pelo IP do Tailscale (`100.x.y.z`, mostrado no
   final do script e em `allgames doutor`). Pareie com o PIN como em casa.

O PC precisa estar ligado e com a sessão aberta. O Wake-on-LAN do Moonlight funciona na rede de
casa, mas normalmente não pelo Tailscale.

## 6. Jogar pelo navegador (opcional, o "site")

Quando não der para instalar o app, o Moonlight Web transforma o PC num site:

```bash
./scripts/instalar-site.sh
```

- Em casa: abra `http://IP-DO-PC:8080` no navegador do celular.
- Fora de casa e com controle: o navegador só libera controle em HTTPS. Com o Tailscale, ative
  HTTPS no painel do Tailscale (DNS → HTTPS Certificates), rode `sudo tailscale serve --bg 8080` e
  abra `https://<nome-do-pc>.<sua-rede>.ts.net`.

O site tem mais atraso e menos opções de controle que o app. Use o app sempre que puder.
