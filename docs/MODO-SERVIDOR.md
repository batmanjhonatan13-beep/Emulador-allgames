# Deixar o PC ligado como servidor de jogos

A ideia: o PC fica num canto da casa, ligado, e você joga pelo celular quando quiser, na rede de
casa (ou fora, com o Tailscale).

```bash
./scripts/modo-servidor.sh
```

O script:

- **impede o PC de suspender ou hibernar sozinho** (senão o celular perde a conexão);
- liga o **Wake-on-LAN** na placa de rede com cabo, para o Moonlight ligar o PC;
- liga o **login automático** quando o gerenciador de login é o GDM (Pop!\_OS 22.04);
- no GNOME, desliga o bloqueio e o apagar automático da tela.

Para desfazer: `./scripts/modo-servidor.sh --desfazer`.

## O que ajustar à mão

- **COSMIC (Pop!\_OS 24.04):** ligue o login automático em Configurações → Usuários, se a sua
  versão tiver a opção. Senão, deixe a sessão aberta. Desligue o bloqueio automático e o apagar
  da tela nas configurações de energia. O Sunshine captura a tela da sessão aberta. Sem sessão, não
  há o que transmitir.
- **BIOS/UEFI:** ligue "Wake on LAN" (às vezes "Power On by PCI-E") para o PC acordar desligado.
- **Cabo de rede:** o PC no cabo e o celular no Wi-Fi de 5 GHz dão o menor atraso.
- **Sem monitor:** a placa de vídeo precisa de uma tela conectada. Use um adaptador "dummy plug"
  HDMI/DisplayPort barato.

## Acesso só pela rede de casa

Por padrão, tudo fica **dentro da sua rede**:

- o Sunshine aceita o Moonlight só de aparelhos pareados (com o PIN);
- o portal AllGames só responde ao próprio PC (é aberto pelo app "AllGames" dentro do Moonlight);
- nenhuma porta precisa ser aberta no roteador.

Para jogar fora de casa, use o Tailscale (`scripts/instalar-tailscale.sh`), não o redirecionamento
de portas.

## Ligar o PC pelo celular

Com o Wake-on-LAN ligado: no Moonlight, mantenha o dedo sobre o PC (aparece como desligado) e
escolha **Enviar Wake-on-LAN**. Isso funciona na rede de casa. Pelo Tailscale, o pacote de acordar
normalmente não chega, porque o PC está desligado.
