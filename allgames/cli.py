"""Linha de comando do AllGames."""

import argparse
import concurrent.futures
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from . import (
    biblioteca,
    caminhos,
    capas,
    catalogo,
    doutor,
    lojas,
    portal,
    portmaster,
    receitas,
    saves,
    sistemas,
    sunshine,
)


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
    jogo = biblioteca.buscar(args.id, jogos)
    if not jogo.instalado:
        dica = jogo.extra.get("falta") or f"rode: allgames instalar {jogo.id}"
        print(f"{jogo.nome} ainda não está pronto: {dica}", file=sys.stderr)
        return 1
    argv = {"rom": sistemas.comando, "portmaster": portmaster.comando}.get(jogo.origem, lambda _: None)(jogo)
    if argv and not shutil.which(argv[0]):
        raise RuntimeError(f"{argv[0]} não está instalado no PC")
    # Guarda os saves da partida anterior antes de abrir o jogo de novo.
    saves.fazer_backup(jogo)
    jogo.pasta.mkdir(parents=True, exist_ok=True)
    (jogo.pasta / ".jogado").touch()
    if argv:
        return receitas.jogar_comando(jogo, argv, args.gamescope, jogo.extra.get("combo_sair", False))
    elif jogo.origem in ("steam", "heroic"):
        return lojas.jogar(jogo)
    else:
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


def cmd_roms(jogos, args) -> int:
    dados = sistemas.carregar()
    caminhos.originais().mkdir(parents=True, exist_ok=True)
    criadas = sistemas.preparar_pastas(dados)
    if criadas:
        print(f"Pastas criadas em {sistemas.roms_dir()} (os mesmos nomes do ArkOS).\n")
    emuladores, lista = dados
    print(f"{'PASTA':<16} {'SISTEMA':<22} {'ROMS':>5}  EMULADOR")
    for sistema in lista:
        quantidade = len(sistemas.roms(sistema))
        emulador = emuladores[sistema.emulador]
        ok, falta = sistemas.pronto(emulador, sistema)
        situacao = "pronto" if ok else falta
        if quantidade or args.todos:
            print(f"{sistema.id:<16} {sistema.nome:<22} {quantidade:>5}  {emulador.nome}: {situacao}")
    print(f"\nROMs em {sistemas.roms_dir()}/<pasta>, BIOS em {sistemas.bios_dir()}")
    print("Instale os emuladores que faltam com: allgames emuladores instalar")
    return 0


def cmd_emuladores(jogos, args) -> int:
    dados = sistemas.carregar()
    emuladores, lista = dados
    if args.acao == "instalar":
        avisos = sistemas.instalar(args.alvos, dados, todos=args.todos)
        for aviso in avisos:
            print(f"! {aviso}")
        print("✔ Pronto. As ROMs desses sistemas já podem ser abertas pelo portal.")
        return 0
    print(f"{'EMULADOR':<12} {'SITUAÇÃO':<10} SISTEMAS")
    for chave, emulador in emuladores.items():
        ok, _ = sistemas.pronto(emulador)
        nomes = ", ".join(s.nome for s in lista if s.emulador == chave)
        print(f"{chave:<12} {'pronto' if ok else 'falta':<10} {nomes}")
        if emulador.aviso and not ok:
            print(f"{'':<23} {emulador.aviso}")
    return 0


def cmd_lojas(jogos, args) -> int:
    if args.registrar_steam:
        if lojas.registrar_biblioteca_steam(Path(args.registrar_steam)):
            print(f"✔ {args.registrar_steam} agora é uma biblioteca da Steam")
        return 0
    steam, heroic = lojas.steam_jogos(), lojas.heroic_jogos()
    for nome, lista, dica in [
        ("Steam", steam, "sem chave da Web API aparecem só os instalados (veja docs/LOJAS.md)"),
        ("Heroic (Epic, GOG, Amazon)", heroic, "abra o Heroic e entre nas suas contas"),
    ]:
        instalados = sum(j.instalado for j in lista)
        print(f"{nome}: {len(lista)} jogos, {instalados} instalados" + ("" if lista else f" — {dica}"))
        if args.detalhes:
            for jogo in lista:
                print(f"  {'✔' if jogo.instalado else ' '} {jogo.nome}  ({jogo.id})")
    return 0


def cmd_preparar(jogos, args) -> int:
    """Deixa tudo pronto para clicar e jogar (é o que o Docker roda ao ligar)."""
    print(time.strftime("== %d/%m/%Y %H:%M:%S: preparando o AllGames"))
    dados = sistemas.carregar()
    caminhos.originais().mkdir(parents=True, exist_ok=True)
    criadas = sistemas.preparar_pastas(dados)
    if criadas:
        print(f"Pastas de ROMs criadas em {sistemas.roms_dir()}")
    if portmaster.instalado():
        portmaster.preparar_ambiente()
        print("PortMaster pronto")
    avisos = [] if args.sem_emuladores else sistemas.instalar([], dados, todos=True)
    if args.lojas:
        for app, nome in (("com.heroicgameslauncher.hgl", "Heroic"),):
            try:
                sistemas.instalar_flatpak(app)
                print(f"{nome} pronto")
            except (RuntimeError, OSError, subprocess.CalledProcessError) as erro:
                avisos.append(f"{nome}: falhou ({erro})")
    if not args.sem_capas:
        cmd_capas(jogos, args)
    for aviso in avisos:
        print(f"! {aviso}")
    print("== pronto")
    return 0


def cmd_capas(jogos, args) -> int:
    """Baixa de uma vez as capas que faltam (o portal também baixa sozinho, conforme você rola a lista)."""
    todos = [j for j in biblioteca.todos(jogos) if j.capa or j.extra.get("capa_local")]
    print(f"Conferindo as capas de {len(todos)} jogos (as que faltam vêm do acervo libretro-thumbnails)")
    com_capa = 0
    with concurrent.futures.ThreadPoolExecutor(8) as tarefas:
        for i, capa in enumerate(tarefas.map(capas.obter, todos), 1):
            com_capa += capa is not None
            if i % 500 == 0 or i == len(todos):
                print(f"  {i}/{len(todos)} conferidos, {com_capa} com capa", flush=True)
    print(f"✔ {com_capa} de {len(todos)} jogos com capa")
    return 0


class _AcaoDoPortmaster(argparse.Action):
    """A primeira palavra é a ação (instalar, desinstalar) ou já faz parte da busca."""

    def __call__(self, parser, namespace, valores, option_string=None):
        if valores and valores[0] in ("buscar", "instalar", "desinstalar"):
            namespace.acao, valores = valores[0], valores[1:]
        setattr(namespace, self.dest, valores)


def cmd_portmaster(jogos, args) -> int:
    if args.acao == "instalar":
        for nome in args.ports:
            portmaster.instalar(nome if nome.endswith(".zip") else f"{nome}.zip")
        return 0
    if args.acao == "desinstalar":
        for nome in args.ports:
            portmaster.desinstalar(nome if nome.endswith(".zip") else f"{nome}.zip")
        return 0
    if not portmaster.instalado():
        print(
            f"O PortMaster não está instalado em {portmaster.pasta_ferramentas()}: rode scripts/instalar-portmaster.sh"
        )
        return 1
    termo = " ".join(args.ports).lower()
    lista = [j for j in portmaster.jogos() if termo in j.nome.lower()]
    for jogo in lista:
        marca = "✔" if jogo.instalado else " "
        aviso = "  (precisa dos arquivos do jogo)" if jogo.extra.get("aviso") else ""
        print(f"{marca} {jogo.extra['nome_zip']:<32} {jogo.nome}{aviso}")
    print(f"\n{len(lista)} ports que rodam neste PC. Instale com: allgames portmaster instalar NOME")
    return 0


def cmd_portal(jogos: list[catalogo.Jogo], args) -> int:
    # Lê catálogo, pastas de ROMs e lojas a cada atualização da tela: ROMs novas aparecem sozinhas.
    return portal.servir(lambda: biblioteca.todos(), args.porta, args.publico, args.kiosk, args.gamescope)


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

    p = sub.add_parser("roms", help="pastas de ROMs por console (estilo ArkOS) e quantas ROMs há em cada")
    p.add_argument("--todos", action="store_true", help="mostra também os sistemas sem ROMs")
    p.set_defaults(func=cmd_roms)

    p = sub.add_parser("emuladores", help="lista ou instala os emuladores")
    p.add_argument(
        "acao", nargs="?", choices=["instalar"], help="instalar: sem alvos, instala o que as suas ROMs pedem"
    )
    p.add_argument("alvos", nargs="*", metavar="SISTEMA_OU_EMULADOR")
    p.add_argument("--todos", action="store_true", help="instala os emuladores de todos os consoles")
    p.set_defaults(func=cmd_emuladores)

    p = sub.add_parser("capas", help="baixa as capas que faltam (ROMs, catálogo e lojas)")
    p.set_defaults(func=cmd_capas)

    p = sub.add_parser("lojas", help="jogos da Steam e do Heroic (Epic, GOG, Amazon)")
    p.add_argument("--detalhes", action="store_true", help="lista os jogos")
    p.add_argument(
        "--registrar-steam", metavar="PASTA", help="acrescenta uma pasta de jogos já baixados à Steam (fechada)"
    )
    p.set_defaults(func=cmd_lojas)

    p = sub.add_parser("preparar", help="instala emuladores e deixa tudo pronto (usado pelo Docker ao ligar)")
    p.add_argument("--lojas", action="store_true", help="instala também o Heroic (Epic, GOG, Amazon)")
    p.add_argument("--sem-emuladores", action="store_true")
    p.add_argument("--sem-capas", action="store_true", help="não baixa as capas que faltam")
    p.set_defaults(func=cmd_preparar)

    p = sub.add_parser(
        "portmaster",
        help="pesquisa, instala e desinstala ports do PortMaster",
        description="allgames portmaster [busca] | instalar PORT... | desinstalar PORT...",
    )
    p.add_argument("ports", nargs="*", metavar="PORT_OU_BUSCA", action=_AcaoDoPortmaster)
    p.set_defaults(func=cmd_portmaster, acao="buscar")

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
    except (catalogo.ErroCatalogo, ValueError, RuntimeError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
