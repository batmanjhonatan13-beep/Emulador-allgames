"""Gera o docs/AllGames-Guia.pdf, o guia completo para quem nunca usou o AllGames.

Uso (precisa do reportlab: pip install reportlab):
    python docs/guia/gerar_guia.py

A tabela de consoles sai do catalogo/sistemas.toml, então fica igual ao que o AllGames aceita.
"""

import sys
from pathlib import Path

import tomllib
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

REPO = Path(__file__).resolve().parents[2]
SAIDA = REPO / "docs" / "AllGames-Guia.pdf"
COMANDO = (
    "irm https://raw.githubusercontent.com/batmanjhonatan13-beep/Emulador-allgames/"
    "ccr-f2ccb85d-qka26y/scripts/instalar-windows.ps1 | iex"
)
PASTA_ROMS = r"C:\Users\SEU_NOME\AllGames\roms"

# ------------------------------------------------------------------ fontes e cores

FONTES = [Path("/usr/share/fonts/truetype/noto"), Path("/usr/share/fonts/truetype/dejavu")]


def _registrar_fontes() -> tuple[str, str, str]:
    noto = FONTES[0]
    if (noto / "NotoSans-Regular.ttf").exists():
        pdfmetrics.registerFont(TTFont("Texto", str(noto / "NotoSans-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Texto-Negrito", str(noto / "NotoSans-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("Mono", str(noto / "NotoSansMono-Regular.ttf")))
    else:
        dejavu = FONTES[1]
        pdfmetrics.registerFont(TTFont("Texto", str(dejavu / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("Texto-Negrito", str(dejavu / "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("Mono", str(dejavu / "DejaVuSansMono.ttf")))
    pdfmetrics.registerFontFamily("Texto", normal="Texto", bold="Texto-Negrito")
    return "Texto", "Texto-Negrito", "Mono"


TEXTO, NEGRITO, MONO = _registrar_fontes()
VERDE = colors.HexColor("#1E8E4E")
VERDE_CLARO = colors.HexColor("#E7F5EC")
LARANJA = colors.HexColor("#B86A00")
LARANJA_CLARO = colors.HexColor("#FFF3E0")
TINTA = colors.HexColor("#1D2127")
CINZA = colors.HexColor("#5B6470")
LINHA = colors.HexColor("#D9DEE4")
FUNDO_CODIGO = colors.HexColor("#F1F3F6")
ESCURO = colors.HexColor("#0D0F12")

ESTILOS = {
    "corpo": ParagraphStyle("corpo", fontName=TEXTO, fontSize=10.5, leading=15.5, textColor=TINTA, spaceAfter=7),
    "h1": ParagraphStyle(
        "h1", fontName=NEGRITO, fontSize=20, leading=25, textColor=TINTA, spaceBefore=4, spaceAfter=12
    ),
    "h2": ParagraphStyle(
        "h2", fontName=NEGRITO, fontSize=13.5, leading=18, textColor=VERDE, spaceBefore=12, spaceAfter=6
    ),
    "passo": ParagraphStyle("passo", fontName=TEXTO, fontSize=10.5, leading=15.5, textColor=TINTA),
    "lista": ParagraphStyle(
        "lista",
        fontName=TEXTO,
        fontSize=10.5,
        leading=15.5,
        textColor=TINTA,
        leftIndent=14,
        bulletIndent=2,
        spaceAfter=3,
    ),
    "codigo": ParagraphStyle("codigo", fontName=MONO, fontSize=9.3, leading=13.5, textColor=TINTA, wordWrap="CJK"),
    "tabela": ParagraphStyle("tabela", fontName=TEXTO, fontSize=9, leading=12.5, textColor=TINTA),
    "tabela-cabeca": ParagraphStyle(
        "tabela-cabeca", fontName=NEGRITO, fontSize=9, leading=12.5, textColor=colors.white
    ),
    "nota": ParagraphStyle("nota", fontName=TEXTO, fontSize=9, leading=13, textColor=CINZA),
}

# ------------------------------------------------------------------ peças do texto


def p(texto: str, estilo: str = "corpo") -> Paragraph:
    return Paragraph(texto, ESTILOS[estilo])


def h1(texto: str) -> list:
    return [CondPageBreak(6 * cm), Paragraph(texto, ESTILOS["h1"])]


def h2(texto: str) -> Paragraph:
    return Paragraph(texto, ESTILOS["h2"])


def lista(itens: list[str]) -> list:
    return [Paragraph(item, ESTILOS["lista"], bulletText="•") for item in itens]


def passos(itens: list[str], inicio: int = 1) -> Table:
    """Passo a passo numerado, com o número num quadrinho verde."""
    numero = ParagraphStyle(
        "numero", fontName=NEGRITO, fontSize=10, leading=12, textColor=colors.white, alignment=TA_CENTER
    )
    linhas = [[Paragraph(str(i), numero), p(texto, "passo")] for i, texto in enumerate(itens, inicio)]
    tabela = Table(linhas, colWidths=[0.75 * cm, None])
    tabela.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), VERDE),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -2), 4, colors.white),
            ]
        )
    )
    return tabela


def caixa(titulo: str, texto: str, cor, fundo) -> KeepTogether:
    corpo = Paragraph(f"<font name='{NEGRITO}' color='{cor.hexval()}'>{titulo}</font><br/>{texto}", ESTILOS["corpo"])
    tabela = Table([[corpo]], colWidths=[None])
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fundo),
                ("LINEBEFORE", (0, 0), (0, -1), 3, cor),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return KeepTogether([Spacer(1, 4), tabela, Spacer(1, 8)])


def dica(texto: str) -> KeepTogether:
    return caixa("Dica", texto, VERDE, VERDE_CLARO)


def atencao(texto: str) -> KeepTogether:
    return caixa("Atenção", texto, LARANJA, LARANJA_CLARO)


def codigo(texto: str) -> KeepTogether:
    tabela = Table([[p(texto, "codigo")]], colWidths=[None])
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FUNDO_CODIGO),
                ("BOX", (0, 0), (-1, -1), 0.6, LINHA),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return KeepTogether([tabela, Spacer(1, 8)])


def tabela(cabecalho: list[str], linhas: list[list[str]], larguras: list[float]) -> Table:
    dados = [[p(c, "tabela-cabeca") for c in cabecalho]] + [[p(c, "tabela") for c in linha] for linha in linhas]
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TINTA),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINHA),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def diagrama() -> Drawing:
    """PC -> Wi-Fi -> celular."""
    largura, altura = 16.6 * cm, 3.6 * cm
    d = Drawing(largura, altura)
    caixas = [
        ("Seu PC", "roda os jogos", "(Sunshine + AllGames)"),
        ("Wi-Fi da casa", "leva a imagem", "e os botões"),
        ("Seu celular", "mostra o jogo", "(app Moonlight)"),
    ]
    w, h, espaco = 4.4 * cm, 2.6 * cm, (largura - 3 * 4.4 * cm) / 2
    for i, (titulo, linha1, linha2) in enumerate(caixas):
        x = i * (w + espaco)
        d.add(Rect(x, 0.5 * cm, w, h, rx=10, ry=10, fillColor=VERDE_CLARO, strokeColor=VERDE, strokeWidth=1.2))
        d.add(
            String(
                x + w / 2,
                0.5 * cm + h - 0.85 * cm,
                titulo,
                fontName=NEGRITO,
                fontSize=12,
                fillColor=TINTA,
                textAnchor="middle",
            )
        )
        d.add(
            String(
                x + w / 2,
                0.5 * cm + h - 1.5 * cm,
                linha1,
                fontName=TEXTO,
                fontSize=9,
                fillColor=CINZA,
                textAnchor="middle",
            )
        )
        d.add(
            String(
                x + w / 2,
                0.5 * cm + h - 2.0 * cm,
                linha2,
                fontName=TEXTO,
                fontSize=9,
                fillColor=CINZA,
                textAnchor="middle",
            )
        )
        if i < 2:
            inicio, fim, y = x + w + 0.15 * cm, x + w + espaco - 0.15 * cm, 0.5 * cm + h / 2
            d.add(Line(inicio, y, fim - 0.25 * cm, y, strokeColor=VERDE, strokeWidth=2))
            d.add(
                Polygon(
                    [fim, y, fim - 0.3 * cm, y + 0.15 * cm, fim - 0.3 * cm, y - 0.15 * cm],
                    fillColor=VERDE,
                    strokeColor=VERDE,
                )
            )
    return d


# ------------------------------------------------------------------ conteúdo


def consoles() -> list[list[str]]:
    dados = tomllib.loads((REPO / "catalogo/sistemas.toml").read_text())
    emuladores = dados["emulador"]
    linhas = []
    for s in dados["sistema"]:
        emulador = emuladores[s["emulador"]]
        if not emulador.get("windows"):
            continue  # ainda não roda no Windows
        precisa = "; ".join(s.get("bios", [])) or "não precisa"
        if s["id"] == "switch":
            precisa = "chaves e firmware do seu Switch (veja abaixo)"
        elif s["id"] == "xbox":
            precisa = "arquivos do seu Xbox (veja abaixo)"
        elif s["id"] == "xbox360":
            precisa = "não precisa (emulador experimental)"
        extensoes = ", ".join("." + e for e in s["extensoes"])
        linhas.append([s["nome"], f"<font name='{MONO}'>{s['id']}</font>", extensoes, precisa])
    return linhas


def conteudo() -> list:
    c = []
    c += h1("Sumário")
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("toc1", fontName=TEXTO, fontSize=11, leading=20, leftIndent=0, textColor=TINTA),
    ]
    c += [toc, PageBreak()]

    # 1
    c += h1("1. O que é o AllGames")
    c.append(
        p(
            "O AllGames transforma o seu PC num <b>videogame que você joga pelo celular</b>. Os jogos rodam no "
            "PC, que tem força de sobra, e o celular só recebe a imagem e manda os botões. É parecido com o "
            'Xbox Cloud Gaming, só que a "nuvem" é o seu próprio computador.'
        )
    )
    c.append(diagrama())
    c.append(
        p(
            "Tudo aparece numa tela com as capas dos jogos, no estilo do Game Pass. Você escolhe o jogo "
            "tocando ou com o controle, e ele abre no emulador certo: Super Nintendo, PlayStation, Game Boy, "
            "Nintendo 64, PSP, PS2, Switch e muitos outros."
        )
    )
    c.append(h2("O que você precisa"))
    c += lista(
        [
            "Um <b>PC com Windows 10 ou 11</b> e uma placa de vídeo dos últimos anos (NVIDIA, AMD ou Intel).",
            "<b>Internet em casa</b> com Wi-Fi. O PC de preferência ligado no cabo de rede.",
            "Um <b>celular</b> Android ou iPhone.",
            "Um <b>controle</b> (opcional): dá para jogar com os botões que aparecem na tela do celular.",
            "Os <b>seus jogos</b> (ROMs) e, para alguns consoles, a BIOS do seu console.",
        ]
    )
    c.append(
        atencao(
            "O AllGames não baixa jogos, BIOS, chaves ou firmware. Use os dos seus próprios cartuchos, discos "
            "e consoles (por exemplo, a pasta de jogos do cartão de um R36S)."
        )
    )

    # 2
    c += h1("2. Instalar no PC")
    c.append(
        p(
            "A instalação é feita por um único comando. Ele baixa e configura tudo sozinho: o <b>Sunshine</b> "
            "(que transmite para o celular), o <b>RetroArch</b> e os outros emuladores, e o próprio AllGames."
        )
    )
    c.append(
        passos(
            [
                "Clique no <b>menu Iniciar</b>, digite <b>PowerShell</b> e abra o <b>Windows PowerShell</b>.",
                "Copie o comando abaixo, clique com o <b>botão direito</b> dentro da janela azul (isso cola) e "
                "aperte <b>Enter</b>. Ele é <b>uma linha só</b>: o jeito mais seguro de copiar é pela página do "
                f"AllGames no GitHub (<font name='{MONO}'>github.com/batmanjhonatan13-beep/Emulador-allgames</font>), "
                "no botão de copiar ao lado do comando, na parte <i>Instalação no Windows</i>.",
            ]
        )
    )
    c.append(codigo(COMANDO))
    c.append(
        passos(
            [
                "Vai aparecer uma janela perguntando se o app pode fazer alterações: clique em <b>Sim</b>. Uma "
                "nova janela azul continua a instalação.",
                "Espere. Na primeira vez leva de <b>10 a 30 minutos</b>, porque ele baixa os emuladores.",
                "Ele pergunta se você tem uma <b>pasta com os seus jogos</b>. Digite <b>S</b> para escolher a "
                "pasta (por exemplo, o cartão do R36S ou um pendrive) ou só aperte <b>Enter</b> para pular e "
                "copiar depois.",
                "Ele pede um <b>usuário e uma senha para o Sunshine</b>. Invente os dois e <b>anote</b>: você "
                "vai usar para parear o celular. A senha não aparece enquanto você digita, é normal.",
                'No fim aparece <b>"Pronto!"</b> e o <b>IP do PC</b> (algo como 192.168.0.10). Anote o IP.',
            ],
            inicio=3,
        )
    )
    c.append(p("Na área de trabalho aparecem dois atalhos novos:"))
    c += lista(
        [
            "<b>Jogos do AllGames</b>: a pasta onde você coloca os jogos.",
            "<b>Parear celular (Sunshine)</b>: a página onde você digita o PIN do celular.",
        ]
    )
    c.append(
        dica(
            "Para <b>atualizar</b> o AllGames no futuro, é só rodar o mesmo comando de novo. Os seus jogos, "
            "saves e configurações não são apagados."
        )
    )
    c.append(h2("Deixe o PC pronto para jogar"))
    c += lista(
        [
            "Deixe o PC <b>ligado</b>. Se ele dormir, o celular não acha. Em <i>Configurações &gt; Sistema &gt; "
            "Energia</i>, coloque a suspensão em <b>Nunca</b> quando estiver na tomada.",
            "Se o PC estiver na tela de bloqueio, tudo bem: o celular mostra essa tela e você digita a senha "
            "do Windows pelo teclado do Moonlight (toque na tela com 3 dedos).",
        ]
    )
    c.append(
        p(
            "Usa Linux (Pop!_OS)? Lá o AllGames roda num container Docker, com tela e Steam próprias, e o PC "
            "continua livre enquanto alguém joga. Veja <i>docs/DOCKER.md</i> no repositório.",
            "nota",
        )
    )
    c.append(
        atencao(
            "No Windows, o celular mostra a <b>mesma tela do PC</b>. Enquanto alguém joga pelo celular, não "
            "dá para usar o PC para outra coisa ao mesmo tempo."
        )
    )

    # 3
    c += h1("3. Instalar o Moonlight no celular")
    c.append(
        p(
            "O <b>Moonlight</b> é o app gratuito que mostra a tela do PC no celular. Ele existe para Android, "
            "iPhone, TV Android, Apple TV e até para outro PC."
        )
    )
    c.append(
        passos(
            [
                "Abra a <b>Play Store</b> (Android) ou a <b>App Store</b> (iPhone) e procure <b>Moonlight Game "
                "Streaming</b>. Confira se o desenvolvedor é o <b>Moonlight Game Streaming Project</b>: há apps "
                "com nomes parecidos que não são o oficial.",
                "Instale e abra. Se o PC aparecer sozinho na lista, ótimo. Se não aparecer, toque no <b>+</b> e "
                "digite o <b>IP do PC</b> que você anotou.",
                "Toque no PC (ele tem um cadeado). O celular mostra um <b>PIN de 4 números</b>. "
                "<b>Não feche essa mensagem.</b>",
                "No PC, abra o atalho <b>Parear celular (Sunshine)</b>. O navegador avisa que o site não é "
                "seguro: é normal, a página é do seu próprio PC. Clique em <i>Avançado &gt; Continuar</i>.",
                "Entre com o <b>usuário e a senha do Sunshine</b>, digite o <b>PIN</b>, dê um nome ao aparelho "
                '(por exemplo, "celular") e envie.',
                "Pronto: o cadeado some. Toque no PC e depois em <b>AllGames</b>.",
            ]
        )
    )
    c.append(
        dica(
            'Se aparecer o erro <i>"A pairing session with this uniqueid already in progress"</i>, você '
            "tocou duas vezes no PC. Feche o Moonlight, abra de novo e toque <b>uma vez</b> só."
        )
    )
    c.append(h2("Ajustes que deixam tudo melhor"))
    c.append(p("Na tela inicial do Moonlight, toque na <b>engrenagem</b>:"))
    c += lista(
        [
            "<b>Resolução</b>: 1080p se o Wi-Fi for bom; 720p se a imagem travar.",
            "<b>Taxa de quadros</b>: 60 FPS.",
            'Em <b>Configurações de Controles</b>, <b>desmarque</b> "Usar a tela como um trackpad". Assim, '
            "tocar numa capa clica exatamente nela.",
            'Se não tiver controle, <b>marque</b> "Mostrar controles na tela" para ter um controle virtual '
            "por cima do jogo.",
        ]
    )

    # 4
    c += h1("4. Controles")
    c.append(h2("Controle conectado no celular (o melhor jeito)"))
    c.append(
        passos(
            [
                "Ligue o controle no <b>Bluetooth do celular</b> (como um fone de ouvido) ou no cabo USB-C. "
                'Controles do tipo "telescópico", que prendem o celular no meio, também funcionam.',
                "Só <b>depois</b> abra o Moonlight e o AllGames. O Moonlight passa o controle para o PC sozinho, "
                "e o PC enxerga como um controle de Xbox.",
            ]
        )
    )
    c.append(
        dica(
            "Se o controle não responder, saia do AllGames (segure <b>Select + Start</b>), confira se ele "
            "está conectado no Bluetooth do celular e abra de novo."
        )
    )
    c.append(h2("Controle na tela"))
    c.append(
        p(
            'Sem controle, use os botões virtuais do Moonlight (veja "Ajustes" no capítulo 3). Eles funcionam '
            "como um controle de verdade, inclusive o Select + Start para sair do jogo."
        )
    )
    c.append(CondPageBreak(7 * cm))
    c.append(h2("Qual botão é qual"))
    c.append(
        p(
            "O AllGames usa os nomes do controle de Xbox. Nos jogos de outros consoles, a <b>posição</b> do "
            "botão é a mesma:"
        )
    )
    c.append(
        tabela(
            ["Posição", "Xbox", "PlayStation", "Nintendo"],
            [
                ["Embaixo", "A", "X (xis)", "B"],
                ["Direita", "B", "O (bola)", "A"],
                ["Esquerda", "X", "Quadrado", "Y"],
                ["Em cima", "Y", "Triângulo", "X"],
                ["Ombros", "LB / RB", "L1 / R1", "L / R"],
                ["Gatilhos", "LT / RT", "L2 / R2", "ZL / ZR"],
                ["Do meio", "View (Select) / Menu (Start)", "Select / Start", "- / +"],
            ],
            [3, 4.4, 4.4, 4.8],
        )
    )

    # 5
    c += h1("5. Usando o AllGames")
    c.append(p("No Moonlight, toque em <b>AllGames</b>. A tela tem cinco abas no topo:"))
    c.append(
        tabela(
            ["Aba", "O que tem"],
            [
                ["Início", 'o último jogo em destaque, "Continue jogando" e uma fileira por console'],
                ["Recentes", "todos os jogos que você já abriu, do mais recente para o mais antigo"],
                ["Instalados", "o que você instalou à parte, como os jogos da Steam (no topo, o que está instalando)"],
                ["Biblioteca", "todos os jogos, com <b>busca</b> e filtros por console"],
                ["Downloads", "o espaço livre no disco e o progresso dos downloads"],
            ],
            [3, 13.6],
        )
    )
    c.append(
        p(
            "Escolha o jogo e aperte <b>Jogar</b>. Na Biblioteca aparecem 120 jogos por vez; no fim da lista, "
            "o cartão <b>Mostrar mais</b> carrega os próximos."
        )
    )
    c.append(h2("Seu progresso fica salvo"))
    c += lista(
        [
            "Ao sair com <b>Select + Start</b>, o jogo é salvo exatamente onde você estava. Na próxima vez, ele "
            "continua dali.",
            "O save normal do jogo também é gravado sozinho a cada 10 segundos.",
            "Antes de cada partida, o AllGames guarda uma cópia de segurança dos saves no PC.",
        ]
    )

    # 6
    c.append(CondPageBreak(9 * cm))
    c += h1("6. Botões e atalhos")
    c.append(
        tabela(
            ["Botão", "No AllGames", "No jogo"],
            [
                ["Direcional / analógico", "anda pelas capas", "joga"],
                ["A", "abre / seleciona", "joga"],
                ["B", "volta", "joga"],
                ["LB / RB", "troca de aba", "joga"],
                [
                    "<b>Segurar Select + Start</b> (1 segundo)",
                    "volta da Steam para o AllGames",
                    "<b>sai do jogo salvando</b> e volta para o AllGames",
                ],
                ["Guide (o botão do meio, com o logo)", "abre a Steam", "abre o menu da Steam"],
                ["L3 + R3 (apertar os dois analógicos)", "—", "menu do emulador: salvar/carregar, opções"],
            ],
            [5.2, 5.2, 6.2],
        )
    )
    c.append(h2("No celular"))
    c += lista(
        [
            "<b>3 dedos na tela</b>: abre o teclado (para digitar senhas, buscar jogos).",
            "<b>Botão Voltar</b> do Android: abre o menu do Moonlight (dá para desconectar).",
            "Para encerrar tudo: no Moonlight, segure o dedo no PC e escolha <b>Sair do jogo</b>.",
        ]
    )

    # 7
    c += h1("7. Onde colocar os jogos")
    c.append(
        p(
            f"Os jogos ficam em <font name='{MONO}'>{PASTA_ROMS}</font>, uma pasta por console. O atalho "
            "<b>Jogos do AllGames</b> na área de trabalho abre essa pasta. Copie o jogo para a pasta do console "
            "e ele aparece sozinho no AllGames, com capa. Não precisa reiniciar nada."
        )
    )
    c.append(
        dica(
            "Tem um <b>R36S</b> ou outro portátil com ArkOS? Coloque o cartão no PC e copie <b>todo o conteúdo</b> "
            "da partição <b>EASYROMS</b> para a pasta <i>roms</i>. As pastas têm os mesmos nomes e as capas "
            "já vêm junto."
        )
    )
    c.append(p("Os nomes das pastas e os tipos de arquivo aceitos:"))
    c.append(tabela(["Console", "Pasta", "Arquivos", "BIOS"], consoles(), [3.4, 3.4, 4.3, 5.5]))
    c.append(Spacer(1, 6))
    c.append(h2("A BIOS e os arquivos dos consoles"))
    c.append(
        p(
            "Alguns consoles precisam de arquivos do console de verdade. Eles vão na pasta "
            f"<font name='{MONO}'>roms\\bios</font>:"
        )
    )
    c += lista(
        [
            f"<b>PlayStation</b>: <font name='{MONO}'>scph5501.bin</font> em <i>bios</i>. Sem ela, a maioria "
            "dos jogos abre mesmo assim, mas com a BIOS fica mais compatível.",
            f"<b>PlayStation 2</b>: a BIOS do seu PS2 em <font name='{MONO}'>bios\\pcsx2\\bios</font>.",
            f"<b>Switch</b>: <font name='{MONO}'>prod.keys</font>, <font name='{MONO}'>title.keys</font> e a "
            f"pasta <font name='{MONO}'>firmware</font> em <font name='{MONO}'>bios\\switch</font>. O "
            "AllGames instala no emulador (Eden) sozinho. Na primeira vez, escolha o controle em "
            "<i>Emulação &gt; Configurar &gt; Controles</i>.",
            f"<b>Xbox</b>: <font name='{MONO}'>mcpx_1.0.bin</font>, a BIOS e o "
            f"<font name='{MONO}'>xbox_hdd.qcow2</font> em <font name='{MONO}'>bios\\xbox</font>.",
            "<b>Sega CD, Saturn e PC Engine CD</b>: os arquivos da tabela acima, em <i>bios</i>.",
        ]
    )

    # 8
    c += h1("8. Steam")
    c.append(
        p(
            "Os jogos da Steam não aparecem no AllGames: eles ficam na própria Steam, que já tem uma tela feita "
            "para controle (o <b>Big Picture</b>)."
        )
    )
    c += lista(
        [
            "Para abrir: aperte o botão <b>Guide</b> do controle, ou toque em <b>Steam</b> no topo do AllGames.",
            "Para voltar ao AllGames: <b>segure Select + Start</b>.",
            "Para sair de um jogo da Steam: aperte <b>Guide</b> e escolha <b>Sair do jogo</b>.",
            "Instale os jogos pela própria Steam. Ela precisa estar aberta e com a sua conta no PC.",
        ]
    )

    # 9
    c.append(CondPageBreak(10 * cm))
    c += h1("9. Jogar fora de casa")
    c.append(
        p(
            "Na mesma rede Wi-Fi, tudo funciona direto. Para jogar na casa de outra pessoa ou no 4G/5G, use o "
            "<b>Tailscale</b>, que cria uma ligação segura entre o celular e o PC:"
        )
    )
    c.append(
        passos(
            [
                "Instale o <b>Tailscale</b> no PC (tailscale.com) e no celular (Play Store / App Store).",
                "Entre com a <b>mesma conta</b> nos dois.",
                "No Moonlight, adicione o PC pelo <b>IP do Tailscale</b> (começa com 100., aparece no app do "
                "Tailscale no PC).",
            ]
        )
    )
    c.append(
        atencao(
            "Jogar fora de casa depende da internet <b>de envio</b> da sua casa: precisa de pelo menos "
            "10 Mbps. Se travar, diminua a resolução no Moonlight."
        )
    )

    # 10
    c += h1("10. Problemas comuns")
    problemas = [
        [
            "O PC não aparece no Moonlight",
            "Confira se o celular está no mesmo Wi-Fi e se o PC está ligado (e não dormindo). Adicione pelo "
            "<b>+</b> com o IP do PC. Se nada resolver, rode o comando de instalação de novo.",
        ],
        [
            "Erro ao parear ou o PIN não é aceito",
            "Feche o Moonlight, abra de novo e toque no PC <b>uma vez só</b>. No PC, digite o PIN logo que ele "
            "aparecer. Se continuar, reinicie o PC.",
        ],
        [
            "Tela preta ao abrir o AllGames",
            "Espere uns 10 segundos. Se continuar, no Moonlight segure o PC &gt; <b>Sair do jogo</b> e abra de "
            "novo. Atualize o driver da placa de vídeo.",
        ],
        [
            "A imagem trava ou atrasa",
            "Use o Wi-Fi de 5 GHz, fique perto do roteador e, se der, ligue o PC no cabo de rede. No Moonlight, "
            "diminua a resolução ou a taxa de bits.",
        ],
        [
            "O jogo não aparece na lista",
            "Confira se ele está na pasta certa (capítulo 7) e com um tipo de arquivo aceito. Feche e abra o AllGames.",
        ],
        ['Aparece "Falta o emulador"', "O PC estava sem internet na instalação. Rode o comando de instalação de novo."],
        ["Um jogo de Switch não abre", "Faltam as chaves (prod.keys) ou o firmware em roms\\bios\\switch."],
        [
            "Não consigo sair do jogo",
            "Segure <b>Select + Start</b> por 1 segundo. Se não der, no Moonlight segure o PC &gt; "
            "<b>Sair do jogo</b> e abra o AllGames de novo.",
        ],
        [
            "Esqueci a senha do Sunshine",
            f"Abra o PowerShell como administrador e rode: <font name='{MONO}'>&amp; \"C:\\Program Files\\Sunshine"
            '\\sunshine.exe" --creds NOVO_USUARIO NOVA_SENHA</font>',
        ],
        [
            "Quero desinstalar",
            "Em <i>Configurações &gt; Aplicativos</i>, desinstale Sunshine, RetroArch e Python. A pasta AllGames "
            "tem os seus jogos e saves: só apague se não precisar mais deles.",
        ],
    ]
    c.append(tabela(["Problema", "O que fazer"], problemas, [4.6, 12]))

    # 11
    c += h1("11. Palavras que aparecem por aí")
    c.append(
        tabela(
            ["Palavra", "O que é"],
            [
                ["ROM", "o arquivo do jogo, copiado do cartucho ou do disco"],
                ["BIOS", 'o "sistema" do console, que alguns emuladores precisam'],
                ["Emulador", "o programa que faz o PC funcionar como um console (RetroArch, Eden, xemu...)"],
                ["Sunshine", "o programa no PC que transmite a imagem para o celular"],
                ["Moonlight", "o app do celular que mostra a imagem e manda os botões"],
                ["PIN", "o código de 4 números que liga o celular ao PC pela primeira vez"],
                ["IP", 'o "endereço" do PC na rede de casa, como 192.168.0.10'],
                ["Big Picture", "a tela da Steam feita para controle e TV"],
                ["Save state", 'uma "foto" do jogo naquele exato momento, para continuar dali'],
            ],
            [3.6, 13],
        )
    )
    return c


# ------------------------------------------------------------------ montagem


class Guia(BaseDocTemplate):
    def __init__(self, arquivo: str):
        super().__init__(
            arquivo,
            pagesize=A4,
            leftMargin=2.2 * cm,
            rightMargin=2.2 * cm,
            topMargin=2.2 * cm,
            bottomMargin=2 * cm,
            title="AllGames — Guia completo",
            author="AllGames",
            subject="Como instalar, conectar o celular e jogar",
        )
        quadro = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="texto")
        self.addPageTemplates(
            [
                PageTemplate(id="capa", frames=[quadro], onPage=self._capa),
                PageTemplate(id="texto", frames=[quadro], onPage=self._pagina),
            ]
        )

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            texto = flowable.getPlainText()
            if texto != "Sumário":
                self.notify("TOCEntry", (0, texto, self.page))

    def _capa(self, canvas, doc):
        largura, altura = A4
        canvas.saveState()
        canvas.setFillColor(ESCURO)
        canvas.rect(0, 0, largura, altura, fill=1, stroke=0)
        imagem = REPO / "portal/capa.png"
        w = 9 * cm
        canvas.drawImage(str(imagem), (largura - w) / 2, altura - 4 * cm - w * 4 / 3, width=w, height=w * 4 / 3)
        canvas.setFillColor(colors.white)
        canvas.setFont(NEGRITO, 30)
        canvas.drawCentredString(largura / 2, 7.2 * cm, "Guia completo")
        canvas.setFillColor(colors.HexColor("#A9B4C2"))
        canvas.setFont(TEXTO, 13)
        canvas.drawCentredString(largura / 2, 6.2 * cm, "Instalar, conectar o celular e jogar,")
        canvas.drawCentredString(largura / 2, 5.5 * cm, "passo a passo, sem precisar entender de computador")
        canvas.setFont(TEXTO, 9)
        canvas.drawCentredString(largura / 2, 2 * cm, "AllGames · Windows 10 e 11 · Moonlight no Android e no iPhone")
        canvas.restoreState()

    def _pagina(self, canvas, doc):
        largura, altura = A4
        canvas.saveState()
        canvas.setStrokeColor(LINHA)
        canvas.setLineWidth(0.6)
        canvas.line(self.leftMargin, altura - 1.4 * cm, largura - self.rightMargin, altura - 1.4 * cm)
        canvas.setFont(NEGRITO, 8.5)
        canvas.setFillColor(VERDE)
        canvas.drawString(self.leftMargin, altura - 1.2 * cm, "AllGames")
        canvas.setFont(TEXTO, 8.5)
        canvas.setFillColor(CINZA)
        canvas.drawString(self.leftMargin + 1.45 * cm, altura - 1.2 * cm, "Guia completo")
        canvas.drawRightString(largura - self.rightMargin, 1.2 * cm, str(doc.page))
        canvas.restoreState()


def gerar(saida: Path = SAIDA) -> Path:
    historia = [NextPageTemplate("texto"), PageBreak(), *conteudo()]
    Guia(str(saida)).multiBuild(historia)
    return saida


if __name__ == "__main__":
    print(gerar(Path(sys.argv[1]) if len(sys.argv) > 1 else SAIDA))
