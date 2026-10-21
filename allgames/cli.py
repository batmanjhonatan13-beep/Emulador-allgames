"""Linha de comando do AllGames."""

import argparse
import sys
from datetime import datetime

from . import caminhos, capas, catalogo, doutor, portal, receitas, saves, sunshine


def cmd_listar(jogos: list[catalogo.Jogo], args) -> int:
    print(f"{'ID':<20} {'JOGO':<42} {'PLATAFORMA':<17} {'TIPO':<9} SITUAÇÃO")
    for jogo in jogos:
        if jogo.instalado:
            situacao = "✔ instalado"
        elif any(not v.ok for v in catalogo.verificar(jogo)):
            situacao = "falta o original"
        else:
            situacao = "pronto para instalar"
        print(f"{jogo.id:<20} {jogo.nome:<42} {jogo.plataforma:<17} {jogo.tipo:<9} {situacao}")
    print(f"\nOriginais ficam em {caminhos.originais()} — detalhes: allgames verificar")
    return 0


def _selecionar(jogos: list[catalogo.Jogo], ids: list[str]) -> list[catalogo.Jogo]:
    return [catalogo.buscar(jogos, i) for i in ids] if ids else jogos


def cmd_verificar(jogos: list[catalogo.Jogo], args) -> int:
    falhas = 0
    for jogo in _selecionar(jogos, args.ids):
        print(f"{jogo.nome} ({jogo.id})")
        if not jogo.originais:
            print("  ✔ não precisa de arquivos originais")
        for v in catalogo.verificar(jogo):
            if not v.ok:
                falhas += 1
                print(f"  ✘ {v.problema}\n      {v.original.descricao}")
            elif v.caminho:
                print(f"  ✔ {v.caminho.name}")
            else:
                print(f"  – {v.original.arquivo} (opcional, ausente): {v.original.descricao}")
    return 1 if falhas else 0


def cmd_instalar(jogos: list[catalogo.Jogo], args) -> int:
    if not args.ids and not args.todos:
        print("Diga quais jogos instalar (ex.: allgames instalar sm64) ou use --todos.", file=sys.stderr)
        return 2
    alvo = jogos if args.todos else _selecionar(jogos, args.ids)
    erros = []
    instalados = []
    for jogo in alvo:
        problemas = [v.problema for v in catalogo.verificar(jogo) if not v.ok]
        if problemas:
            if args.todos:
                print(f"– pulando {jogo.nome}: " + "; ".join(problemas))
            else:
                erros.append(jogo.id)
                print(f"✘ {jogo.nome}: " + "; ".join(problemas), file=sys.stderr)
            continue
        print(f"\n### Instalando {jogo.nome} ###")
        if receitas.instalar(jogo) == 0:
            instalados.append(jogo.id)
        else:
            erros.append(jogo.id)
            print(f"✘ falhou a instalação de {jogo.nome}", file=sys.stderr)
    if instalados:
        print(f"\n✔ Instalados: {', '.join(instalados)}")
        if not args.sem_sincronizar:
            cmd_sincronizar(jogos, argparse.Namespace(gamescope=None, sem_reiniciar=False))
    if erros:
        print(f"✘ Com problema: {', '.join(erros)}", file=sys.stderr)
    return 1 if erros else 0


def cmd_jogar(jogos: list[catalogo.Jogo], args) -> int:
    jogo = catalogo.buscar(jogos, args.id)
    if not jogo.instalado:
        print(f"{jogo.nome} não está instalado. Rode: allgames instalar {jogo.id}", file=sys.stderr)
        return 1
    # Guarda os saves da partida anterior antes de abrir o jogo de novo.
    saves.fazer_backup(jogo)
    (jogo.pasta / ".jogado").touch()
    receitas.jogar(jogo, gamescope=args.gamescope)
    return 0  # não chega aqui: o processo vira o jogo


def cmd_sincronizar(jogos: list[catalogo.Jogo], args) -> int:
    arquivo = sunshine.arquivo_apps()
    atual = sunshine.ler(arquivo)
    gamescope = args.gamescope
    if gamescope is None:  # sem --gamescope/--no-gamescope: mantém o que já estava publicado
        gamescope = any("--gamescope" in a.get("cmd", "") for a in atual.get("apps", []) if sunshine.eh_nosso(a))
    instalados = [j for j in jogos if j.instalado]
    apps = [sunshine.app_do_portal(gamescope)]
    apps += [sunshine.app_do_jogo(j, capas.obter(j), gamescope) for j in instalados]
    novo, conflitos = sunshine.mesclar(atual, apps)
    backup = sunshine.gravar(arquivo, novo)
    print(f"✔ portal AllGames + {len(instalados)} jogo(s) publicados em {arquivo}")
    if backup:
        print(f"  cópia do arquivo anterior: {backup}")
    for nome in conflitos:
        print(f"  ! já existe um app seu chamado {nome!r} no Sunshine; renomeie-o para o AllGames publicar o dele")
    if args.sem_reiniciar:
        print("  reinicie o Sunshine para o celular ver a lista nova")
    elif sunshine.reiniciar():
        print("  Sunshine reiniciado: atualize a lista de jogos no Moonlight")
    else:
        print("  o serviço do Sunshine não está rodando; a lista vale quando ele iniciar")
    return 0


def cmd_doutor(jogos, args) -> int:
    return doutor.executar()


def cmd_portal(jogos: list[catalogo.Jogo], args) -> int:
    return portal.servir(jogos, args.porta, args.publico, args.kiosk, args.gamescope)


def _quando(timestamp: float | None) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M") if timestamp else "—"


def cmd_saves(jogos: list[catalogo.Jogo], args) -> int:
    if not args.id:
        print(f"{'ID':<22} {'ÚLTIMO SAVE':<17} {'ARQUIVOS':>8} {'CÓPIAS':>7}")
        for jogo in jogos:
            if jogo.instalado:
                n = len(saves.arquivos(jogo))
                print(f"{jogo.id:<22} {_quando(saves.ultimo_save(jogo)):<17} {n:>8} {len(saves.backups(jogo)):>7}")
        print(f"\nCópias de segurança em {caminhos.backups()} — detalhes: allgames saves ID")
        return 0
    jogo = catalogo.buscar(jogos, args.id)
    print(f"{jogo.nome}: progresso salvo no PC")
    if not jogo.saves:
        print("  o catálogo não diz onde este jogo grava os saves")
    for arquivo in saves.arquivos(jogo):
        print(f"  {_quando(arquivo.stat().st_mtime)}  {arquivo}")
    copias = saves.backups(jogo)
    print(f"\nCópias ({len(copias)}), restaure com: allgames restaurar {jogo.id} [NOME]")
    for copia in copias:
        print(f"  {copia.name}")
    return 0


def cmd_backup(jogos: list[catalogo.Jogo], args) -> int:
    for jogo in _selecionar(jogos, args.ids) if args.ids else [j for j in jogos if j.instalado]:
        copia = saves.fazer_backup(jogo)
        if copia:
            print(f"✔ {jogo.nome}: {copia}")
        elif saves.arquivos(jogo):
            print(f"– {jogo.nome}: nada mudou desde a última cópia")
    return 0


def cmd_restaurar(jogos: list[catalogo.Jogo], args) -> int:
    jogo = catalogo.buscar(jogos, args.id)
    copias = {c.name: c for c in saves.backups(jogo)}
    if not copias:
        print(f"{jogo.nome} ainda não tem cópias de saves.", file=sys.stderr)
        return 1
    nome = args.copia or max(copias)
    if nome not in copias:
        print(f"Cópia {nome!r} não existe. Veja: allgames saves {jogo.id}", file=sys.stderr)
        return 1
    for arquivo in saves.restaurar(jogo, copias[nome]):
        print(f"✔ {arquivo}")
    print(f"Saves de {jogo.nome} voltaram para {nome} (o estado anterior também foi guardado).")
    return 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="allgames",
        description="Instala jogos descompilados no seu PC e publica no Sunshine para jogar pelo celular.",
    )
    sub = parser.add_subparsers(dest="comando", required=True, metavar="COMANDO")

    p = sub.add_parser("listar", help="mostra o catálogo e a situação de cada jogo")
    p.set_defaults(func=cmd_listar)

    p = sub.add_parser("verificar", help="confere os arquivos originais (ROMs, ISOs...)")
    p.add_argument("ids", nargs="*", metavar="ID")
    p.set_defaults(func=cmd_verificar)

    p = sub.add_parser("instalar", help="baixa/compila jogos e publica no Sunshine")
    p.add_argument("ids", nargs="*", metavar="ID")
    p.add_argument("--todos", action="store_true", help="instala todos que já têm os originais")
    p.add_argument("--sem-sincronizar", action="store_true", help="não atualiza o Sunshine no final")
    p.set_defaults(func=cmd_instalar)

    p = sub.add_parser("jogar", help="abre um jogo (é o comando que o Sunshine chama)")
    p.add_argument("id", metavar="ID")
    p.add_argument("--gamescope", action="store_true", help="roda dentro do gamescope na resolução do celular")
    p.set_defaults(func=cmd_jogar)

    p = sub.add_parser("sincronizar", help="publica os jogos instalados como apps do Sunshine")
    p.add_argument(
        "--gamescope",
        action=argparse.BooleanOptionalAction,
        help="liga/desliga a abertura dos jogos no gamescope (padrão: mantém como está)",
    )
    p.add_argument("--sem-reiniciar", action="store_true", help="não reinicia o serviço do Sunshine")
    p.set_defaults(func=cmd_sincronizar)

    p = sub.add_parser("portal", help="tela com as capas dos jogos, estilo Game Pass")
    p.add_argument("--kiosk", action="store_true", help="abre o navegador em tela cheia (é o que o Sunshine usa)")
    p.add_argument("--porta", type=int, default=portal.PORTA)
    p.add_argument("--publico", action="store_true", help="aceita acesso pela rede, não só deste PC")
    p.add_argument("--gamescope", action="store_true", help="abre os jogos no gamescope na resolução do celular")
    p.set_defaults(func=cmd_portal)

    p = sub.add_parser("saves", help="mostra onde cada jogo salva no PC e as cópias de segurança")
    p.add_argument("id", nargs="?", metavar="ID")
    p.set_defaults(func=cmd_saves)

    p = sub.add_parser("backup", help="copia os saves agora (também é feito antes de cada partida)")
    p.add_argument("ids", nargs="*", metavar="ID")
    p.set_defaults(func=cmd_backup)

    p = sub.add_parser("restaurar", help="volta os saves de um jogo para uma cópia")
    p.add_argument("id", metavar="ID")
    p.add_argument("copia", nargs="?", metavar="NOME", help="nome da cópia (padrão: a mais recente)")
    p.set_defaults(func=cmd_restaurar)

    p = sub.add_parser("doutor", help="confere se o PC está pronto para o streaming")
    p.set_defaults(func=cmd_doutor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)
    try:
        jogos = catalogo.carregar()
        return args.func(jogos, args)
    except catalogo.ErroCatalogo as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
