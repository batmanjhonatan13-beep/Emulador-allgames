"use strict";

// Portal AllGames: biblioteca com capas, navegável por toque, teclado ou controle.

const ICONES = {
  controle:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 8h10a5 5 0 0 1 4.6 7l-.6 1.4a2.6 2.6 0 0 1-4.3.7L15 15H9l-1.7 2.1a2.6 2.6 0 0 1-4.3-.7L2.4 15A5 5 0 0 1 7 8z"/><path d="M7 11v3M5.5 12.5h3"/><circle cx="16" cy="11.5" r=".6"/><circle cx="18" cy="13.5" r=".6"/></svg>',
  toque:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 11V5.5a1.5 1.5 0 0 1 3 0V11m0-1.5a1.5 1.5 0 0 1 3 0V11m0-.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-.6a6 6 0 0 1-4.8-2.4L4.3 15.6a1.5 1.5 0 0 1 2.3-1.9L9 16"/></svg>',
  play: '<svg class="cheio" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z"/></svg>',
  baixar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5M5 19.5h14"/></svg>',
  disco:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/></svg>',
};

const NOMES_CONTROLES = { controle: "Controle", toque: "Toque" };

const estado = {
  jogos: [],
  jogando: null,
  podeSair: false,
  aba: "inicio",
  filtro: "todos",
  busca: "",
  limiteGrade: 0, // quantos cartões a grade da Biblioteca mostra (cresce com "Mostrar mais")
  temControle: false,
  focado: null,
  inicioPartida: 0,
};

// ---------------------------------------------------------------- utilidades

const $ = (seletor, raiz = document) => raiz.querySelector(seletor);

function el(tag, atributos = {}, ...filhos) {
  const elemento = document.createElement(tag);
  for (const [chave, valor] of Object.entries(atributos)) {
    if (valor === false || valor == null) continue;
    if (chave === "class") elemento.className = valor;
    else if (chave === "html") elemento.innerHTML = valor;
    else if (chave.startsWith("on")) elemento.addEventListener(chave.slice(2), valor);
    else elemento.setAttribute(chave, valor === true ? "" : valor);
  }
  for (const filho of filhos.flat()) {
    if (filho != null) elemento.append(filho);
  }
  return elemento;
}

async function api(caminho, metodo = "GET") {
  const resposta = await fetch(caminho, { method: metodo, headers: { "X-AllGames": "1" } });
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(dados.erro || `erro ${resposta.status}`);
  return dados;
}

function quando(iso) {
  if (!iso) return null;
  const data = new Date(iso);
  const hoje = new Date();
  const ontem = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() - 1);
  const hora = data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  if (data.toDateString() === hoje.toDateString()) return `hoje às ${hora}`;
  if (data.toDateString() === ontem.toDateString()) return `ontem às ${hora}`;
  return `${data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })} às ${hora}`;
}

function normalizar(texto) {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

function precisaDeControle(jogo) {
  return !jogo.controles.includes("toque");
}

let temporizadorMensagem;
function mensagem(texto) {
  const caixa = $("#mensagem");
  caixa.textContent = texto;
  caixa.hidden = false;
  clearTimeout(temporizadorMensagem);
  temporizadorMensagem = setTimeout(() => (caixa.hidden = true), 6000);
}

// ---------------------------------------------------------------- capas e cartões

function arte(jogo, classe = "arte") {
  const iniciais = jogo.nome
    .replace(/[^\p{L}\p{N} ]/gu, "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("");
  let matiz = 0;
  for (const c of jogo.id) matiz = (matiz * 31 + c.charCodeAt(0)) % 360;
  const caixa = el("div", { class: classe, style: `--matiz:${matiz}` }, el("span", { class: "iniciais" }, iniciais));
  const fontes = [jogo.capa, jogo.capa_alternativa].filter(Boolean);
  if (fontes.length) {
    const img = el("img", { src: fontes.shift(), alt: "", loading: "lazy", decoding: "async", referrerpolicy: "no-referrer" });
    img.addEventListener("load", () => {
      caixa.style.setProperty("--capa", `url("${img.src}")`);
      caixa.classList.add("com-capa");
    });
    img.addEventListener("error", () => (fontes.length ? (img.src = fontes.shift()) : img.remove()));
    caixa.append(img);
  }
  return caixa;
}

function selosControles(jogo, comTexto = false) {
  return el(
    "span",
    { class: `selos${comTexto ? " com-texto" : ""}` },
    jogo.controles.map((c) =>
      el("span", { class: `selo selo-${c}`, title: NOMES_CONTROLES[c], html: ICONES[c] }, comTexto ? NOMES_CONTROLES[c] : null),
    ),
  );
}

function etiqueta(jogo) {
  let texto = null;
  if (jogo.download && !jogo.instalado) {
    const rotulo = jogo.download.estado === "baixando" ? "Baixando" : "Pausado";
    return el("span", { class: `etiqueta${jogo.download.estado === "baixando" ? " etiqueta-ativa" : ""}` }, `${rotulo} ${jogo.download.progresso}%`);
  }
  if (jogo.tarefa === "instalando") texto = "Instalando…";
  else if (jogo.tarefa === "erro") texto = "Erro ao instalar";
  else if (jogo.instalado) return null;
  else if (jogo.origem === "rom") texto = "Falta o emulador";
  else if (jogo.origem !== "catalogo") texto = "Instalar";
  else texto = jogo.falta.length ? "Falta o jogo" : "Instalar no PC";
  return el("span", { class: `etiqueta${jogo.tarefa === "instalando" ? " etiqueta-ativa" : ""}` }, texto);
}

function cartao(jogo) {
  return el(
    "button",
    {
      class: `cartao${jogo.instalado ? "" : " pendente"}`,
      "data-nav": true,
      "data-id": jogo.id,
      "aria-label": jogo.nome,
      onclick: () => abrirDetalhe(jogo),
    },
    arte(jogo),
    etiqueta(jogo),
    jogo.ultimo_save ? el("span", { class: "etiqueta etiqueta-save", html: ICONES.disco }) : null,
    el(
      "span",
      { class: "legenda" },
      el("span", { class: "nome" }, jogo.nome),
      el("span", { class: "sub" }, jogo.plataforma, selosControles(jogo)),
    ),
  );
}

// ---------------------------------------------------------------- telas

function renderizar() {
  const idFocado = estado.focado?.dataset.id;
  renderizarDestaque();
  renderizarFileiras();
  renderizarRecentes();
  renderizarInstalados();
  renderizarBiblioteca();
  $("#sair").hidden = !estado.podeSair;
  const alvo = idFocado && document.querySelector(`.visao:not([hidden]) [data-id="${CSS.escape(idFocado)}"]`);
  if (alvo) focar(alvo, false);
}

function jogoEmDestaque() {
  const instalados = estado.jogos.filter((j) => j.instalado);
  const jogados = instalados.filter((j) => j.jogado_em).sort((a, b) => b.jogado_em.localeCompare(a.jogado_em));
  return jogados[0] || instalados[0] || estado.jogos[0];
}

function renderizarDestaque() {
  const jogo = jogoEmDestaque();
  const caixa = $("#destaque");
  caixa.replaceChildren();
  if (!jogo) {
    caixa.append(el("div", { class: "destaque-vazio" }, "O catálogo está vazio."));
    return;
  }
  caixa.style.setProperty("--capa", jogo.capa ? `url("${jogo.capa}")` : "none");
  const acao = jogo.acoes.includes("jogar")
    ? el("button", { class: "botao primario", "data-nav": true, onclick: () => jogar(jogo), html: `${ICONES.play} Jogar` })
    : el("button", { class: "botao", "data-nav": true, onclick: () => abrirDetalhe(jogo) }, "Como jogar");
  caixa.append(
    arte(jogo, "arte arte-destaque"),
    el(
      "div",
      { class: "destaque-texto" },
      el("span", { class: "sobretitulo" }, jogo.jogado_em ? "Continue jogando" : jogo.instalado ? "Pronto para jogar" : "No catálogo"),
      el("h1", {}, jogo.nome),
      el("p", { class: "linha-info" }, linhaInfo(jogo)),
      jogo.descricao ? el("p", { class: "descricao" }, jogo.descricao) : null,
      linhaSave(jogo),
      el(
        "div",
        { class: "acoes" },
        acao,
        el("button", { class: "botao", "data-nav": true, onclick: () => abrirDetalhe(jogo) }, "Detalhes"),
        selosControles(jogo, true),
      ),
    ),
  );
}

function linhaInfo(jogo) {
  return [...new Set([jogo.plataforma, jogo.tipo, jogo.colecao].filter(Boolean))].join(" · ");
}

function linhaSave(jogo) {
  const ultimo = quando(jogo.ultimo_save);
  if (!jogo.instalado) return null;
  return el(
    "p",
    { class: "save", html: ICONES.disco },
    ultimo ? `Salvo no PC · último save ${ultimo}` : "O progresso fica salvo no PC",
  );
}

const LIMITE_FILEIRA = 30;
const PAGINA_GRADE = 120;

function fileira(titulo, jogos, filtro = null) {
  if (!jogos.length) return null;
  const mais =
    filtro && jogos.length > LIMITE_FILEIRA
      ? el(
          "button",
          {
            class: "cartao cartao-mais",
            "data-nav": true,
            onclick: () => {
              estado.filtro = filtro;
              estado.limiteGrade = 0;
              renderizarBiblioteca();
              trocarAba("biblioteca");
              focar($(`[data-filtro="${CSS.escape(filtro)}"]`), false);
            },
          },
          el("span", { class: "arte" }, el("span", { class: "iniciais" }, `+${jogos.length - LIMITE_FILEIRA}`)),
          el("span", { class: "legenda" }, el("span", { class: "nome" }, "Ver todos")),
        )
      : null;
  return el(
    "section",
    { class: "fileira" },
    el("h2", {}, titulo, el("span", { class: "contagem" }, String(jogos.length))),
    el("div", { class: "trilho" }, jogos.slice(0, filtro ? LIMITE_FILEIRA : jogos.length).map(cartao), mais),
  );
}

function renderizarFileiras() {
  const jogos = estado.jogos;
  const jogados = jogos.filter((j) => j.instalado && j.jogado_em).sort((a, b) => b.jogado_em.localeCompare(a.jogado_em));
  // Coleções com mais jogos prontos primeiro: o que você já pode jogar fica no alto.
  const prontos = (c) => jogos.filter((j) => j.colecao === c && j.instalado).length;
  const colecoes = [...new Set(jogos.map((j) => j.colecao).filter(Boolean))].sort((a, b) => (prontos(b) > 0) - (prontos(a) > 0));
  $("#fileiras").replaceChildren(
    ...[
      fileira("Continue jogando", jogados.slice(0, LIMITE_FILEIRA)),
      fileira("Prontos para jogar", jogos.filter((j) => j.instalado), "instalados"),
      ...colecoes.map((c) => fileira(c, jogos.filter((j) => j.colecao === c), `c:${c}`)),
      fileira("Outros jogos", jogos.filter((j) => !j.colecao)),
    ].filter(Boolean),
  );
}

// Todos os jogos que você já abriu, do mais recente para o mais antigo.
function renderizarRecentes() {
  const jogados = estado.jogos.filter((j) => j.jogado_em).sort((a, b) => b.jogado_em.localeCompare(a.jogado_em));
  $("#grade-recentes").replaceChildren(
    ...(jogados.length
      ? jogados.slice(0, PAGINA_GRADE).map(cartao)
      : [el("p", { class: "vazio" }, "Os jogos que você abrir aparecem aqui.")]),
  );
}

// O que você instalou (Steam, Epic, GOG, PortMaster, catálogo), como a biblioteca da Steam:
// o que está baixando no alto e, embaixo, o que já dá para abrir. As ROMs ficam na Biblioteca.
function renderizarInstalados() {
  const instalando = estado.jogos.filter((j) => j.tarefa === "instalando" || (j.download && j.download.estado !== "concluido"));
  const instalados = estado.jogos
    .filter((j) => j.origem !== "rom" && j.instalado && !instalando.includes(j))
    .sort((a, b) => (b.jogado_em || "").localeCompare(a.jogado_em || "") || a.nome.localeCompare(b.nome));
  $("#instalando").replaceChildren(...(instalando.length ? [fileira("Instalando agora", instalando)] : []));
  $("#grade-instalados").replaceChildren(
    ...(instalados.length
      ? instalados.map(cartao)
      : [el("p", { class: "vazio" }, "Os jogos que você instalar (Steam, Epic, PortMaster) aparecem aqui.")]),
  );
}

function filtros() {
  const plataformas = [...new Set(estado.jogos.map((j) => j.plataforma))];
  const colecoes = [...new Set(estado.jogos.map((j) => j.colecao).filter((c) => c && !plataformas.includes(c)))];
  const tem = (f) => estado.jogos.some(f);
  const loja = (j) => j.origem === "steam" || j.origem === "heroic";
  return [
    ["todos", "Todos", () => true],
    ["instalados", "Instalados", (j) => j.instalado],
    ["toque", "Jogáveis no toque", (j) => j.controles.includes("toque")],
    ["controle", "Com controle", (j) => j.controles.includes("controle")],
    tem(loja) ? ["lojas", "Steam e lojas", loja] : null,
    tem((j) => j.origem === "rom") ? ["roms", "ROMs", (j) => j.origem === "rom"] : null,
    ...colecoes.map((c) => [`c:${c}`, c, (j) => j.colecao === c]),
    ...plataformas.map((p) => [`p:${p}`, p, (j) => j.plataforma === p]),
  ].filter(Boolean);
}

function renderizarBiblioteca() {
  const lista = filtros();
  // "c:<nome>" de uma coleção que também é plataforma vira o filtro da plataforma.
  const pedido = estado.filtro.startsWith("c:") && !lista.some(([id]) => id === estado.filtro) ? `p:${estado.filtro.slice(2)}` : estado.filtro;
  const atual = lista.find(([id]) => id === pedido) || lista[0];
  $("#filtros").replaceChildren(
    ...lista.map(([id, nome]) =>
      el(
        "button",
        {
          class: `chip${id === atual[0] ? " ativo" : ""}`,
          "data-nav": true,
          "data-filtro": id,
          onclick: () => {
            estado.filtro = id;
            estado.limiteGrade = 0;
            renderizarBiblioteca();
            focar($(`[data-filtro="${CSS.escape(id)}"]`), false);
          },
        },
        nome,
      ),
    ),
  );
  const termo = normalizar(estado.busca);
  const jogos = estado.jogos.filter(atual[2]).filter((j) => !termo || normalizar(`${j.nome} ${j.plataforma}`).includes(termo));
  if (!jogos.length) return $("#grade").replaceChildren(el("p", { class: "vazio" }, "Nenhum jogo aqui."));
  // Com milhares de ROMs, desenhar tudo de uma vez trava a tela e a navegação pelo controle.
  const limite = Math.max(estado.limiteGrade, PAGINA_GRADE);
  const restantes = jogos.length - limite;
  const mais =
    restantes > 0
      ? el(
          "button",
          {
            class: "cartao cartao-mais",
            "data-nav": true,
            onclick: () => {
              estado.limiteGrade = limite + PAGINA_GRADE;
              renderizarBiblioteca();
              focar($("#grade").children[limite]);
            },
          },
          el("span", { class: "arte" }, el("span", { class: "iniciais" }, `+${restantes}`)),
          el("span", { class: "legenda" }, el("span", { class: "nome" }, "Mostrar mais")),
        )
      : null;
  $("#grade").replaceChildren(...jogos.slice(0, limite).map(cartao), ...(mais ? [mais] : []));
}

function trocarAba(aba) {
  estado.aba = aba;
  for (const botao of document.querySelectorAll(".aba")) botao.classList.toggle("ativa", botao.dataset.aba === aba);
  for (const visao of document.querySelectorAll(".visao")) visao.hidden = visao.id !== aba;
  window.scrollTo({ top: 0 });
  if (aba === "downloads") carregarDownloads();
}

// ---------------------------------------------------------------- camadas (detalhe, aviso, jogando)

function camadaAberta() {
  return [...document.querySelectorAll(".camada")].reverse().find((c) => !c.hidden) || null;
}

function abrirCamada(id, conteudo) {
  const camada = $(`#${id}`);
  camada.replaceChildren(conteudo);
  camada.hidden = false;
  camada.dataset.volta = estado.focado?.dataset.id || "";
  focar(camada.querySelector("[data-autofoco]") || camada.querySelector("[data-nav]"));
}

function fecharCamada(camada = camadaAberta()) {
  if (!camada || camada.id === "jogando") return;
  camada.hidden = true;
  const debaixo = camadaAberta();
  if (debaixo && debaixo.id !== "jogando") {
    return focar(debaixo.querySelector("[data-autofoco]") || debaixo.querySelector("[data-nav]"));
  }
  const volta = camada.dataset.volta && document.querySelector(`.visao:not([hidden]) [data-id="${CSS.escape(camada.dataset.volta)}"]`);
  focar(volta || document.querySelector(".visao:not([hidden]) [data-nav]"));
}

function abrirDetalhe(jogo) {
  const explicacao = precisaDeControle(jogo)
    ? "Precisa de controle: use um controle Bluetooth no celular ou ative os controles na tela do Moonlight."
    : jogo.controles.includes("controle")
      ? "Dá para jogar tocando direto na tela ou com controle."
      : "Dá para jogar tocando direto na tela.";
  abrirCamada(
    "detalhe",
    el(
      "div",
      { class: "painel painel-detalhe", role: "dialog", "aria-label": jogo.nome },
      arte(jogo, "arte arte-detalhe"),
      el(
        "div",
        { class: "detalhe-texto" },
        el("h1", {}, jogo.nome),
        el("p", { class: "linha-info" }, linhaInfo(jogo)),
        jogo.descricao ? el("p", { class: "descricao" }, jogo.descricao) : null,
        el("p", { class: "controles-info" }, selosControles(jogo, true), el("span", {}, explicacao)),
        linhaSave(jogo),
        pendencia(jogo),
        el("div", { class: "acoes" }, botoesDeAcao(jogo), el("button", { class: "botao", "data-nav": true, onclick: () => fecharCamada() }, "Voltar")),
      ),
    ),
  );
}

function pendencia(jogo) {
  const linhas = [];
  if (jogo.tarefa === "instalando") linhas.push(el("p", {}, "Instalando no PC… a tela atualiza sozinha quando terminar."));
  if (jogo.tarefa === "erro") linhas.push(el("p", {}, "A instalação falhou. No PC, veja ~/AllGames/logs/instalacoes.log."));
  if (!jogo.instalado && jogo.origem === "catalogo") {
    if (jogo.falta.length) linhas.push(el("p", {}, `Falta o jogo original: ${jogo.falta.join("; ")}.`));
    if (!jogo.acoes.length) linhas.push(el("p", {}, "Depois de colocar o arquivo, instale aqui ou no PC com:"), el("code", {}, `allgames instalar ${jogo.id}`));
  }
  if (!jogo.instalado && jogo.pendente) linhas.push(el("p", {}, `Para jogar: ${jogo.pendente}.`));
  if (jogo.aviso) linhas.push(el("p", {}, jogo.aviso));
  return linhas.length ? el("div", { class: "pendencia" }, linhas) : null;
}

function botoesDeAcao(jogo) {
  const botoes = [];
  if (jogo.acoes.includes("jogar")) {
    botoes.push(el("button", { class: "botao primario", "data-nav": true, "data-autofoco": true, onclick: () => jogar(jogo), html: `${ICONES.play} Jogar` }));
  }
  if (jogo.acoes.includes("instalar") && jogo.tarefa !== "instalando") {
    const texto = jogo.origem === "rom" ? "Instalar o emulador" : "Instalar";
    botoes.push(el("button", { class: "botao primario", "data-nav": true, "data-autofoco": true, onclick: () => executarAcao(jogo, "instalar"), html: `${ICONES.baixar} ${texto}` }));
  }
  if (jogo.acoes.includes("desinstalar")) {
    botoes.push(el("button", { class: "botao perigo", "data-nav": true, onclick: () => confirmarDesinstalar(jogo) }, "Desinstalar"));
  }
  return botoes;
}

function executarAcao(jogo, acao) {
  for (const camada of document.querySelectorAll(".camada:not(#jogando)")) camada.hidden = true;
  api(`/api/${acao}?id=${encodeURIComponent(jogo.id)}`, "POST")
    .then((resposta) => {
      if (resposta.mensagem) mensagem(resposta.mensagem);
      return carregar();
    })
    .catch((erro) => mensagem(`Não deu: ${erro.message}`));
}

function confirmarDesinstalar(jogo) {
  abrirCamada(
    "aviso",
    el(
      "div",
      { class: "painel painel-aviso", role: "alertdialog" },
      el("h2", {}, `Desinstalar ${jogo.nome}?`),
      el("p", {}, "Os arquivos do jogo saem do PC. Saves na nuvem da loja continuam lá."),
      el(
        "div",
        { class: "acoes" },
        el("button", { class: "botao perigo", "data-nav": true, onclick: () => executarAcao(jogo, "desinstalar") }, "Desinstalar"),
        el("button", { class: "botao", "data-nav": true, "data-autofoco": true, onclick: () => fecharCamada() }, "Cancelar"),
      ),
    ),
  );
}

function jogar(jogo, confirmado = false) {
  if (!confirmado && precisaDeControle(jogo) && !estado.temControle) {
    abrirCamada(
      "aviso",
      el(
        "div",
        { class: "painel painel-aviso", role: "alertdialog", "data-jogo": jogo.id },
        el("div", { class: "aviso-icone", html: ICONES.controle }),
        el("h2", {}, "Este jogo precisa de controle"),
        el("p", {}, "Conecte um controle Bluetooth no celular ou ative os controles na tela do Moonlight."),
        el("p", { class: "fraco" }, "Já tem um controle conectado? Aperte qualquer botão nele."),
        el(
          "div",
          { class: "acoes" },
          el("button", { class: "botao primario", "data-nav": true, onclick: () => jogar(jogo, true) }, "Jogar mesmo assim"),
          el("button", { class: "botao", "data-nav": true, "data-autofoco": true, onclick: () => fecharCamada() }, "Cancelar"),
        ),
      ),
    );
    return;
  }
  for (const camada of document.querySelectorAll(".camada:not(#jogando)")) camada.hidden = true;
  api(`/api/jogar?id=${encodeURIComponent(jogo.id)}`, "POST")
    .then(() => mostrarJogando(jogo))
    .catch((erro) => mensagem(`Não deu para abrir ${jogo.nome}: ${erro.message}`));
}

function mostrarJogando(jogo) {
  estado.jogando = jogo.id;
  estado.inicioPartida = Date.now();
  const camada = $("#jogando");
  camada.replaceChildren(
    el(
      "div",
      { class: "painel painel-jogando" },
      arte(jogo, "arte arte-jogando"),
      el("div", { class: "girando" }),
      el("h2", {}, `Jogando ${jogo.nome}`),
      el("p", {}, "O jogo abriu no PC. Quando você sair dele, volta para cá."),
      el("p", { class: "dica-sair" }, "Para sair do jogo: segure Select + Start (no controle ou nos botões da tela do Moonlight)."),
      el("p", { class: "save", html: ICONES.disco }, "O progresso é salvo no PC, com cópia de segurança antes de cada partida."),
      el("button", { class: "botao", onclick: () => api("/api/encerrar", "POST") }, "Encerrar o jogo"),
    ),
  );
  camada.hidden = false;
  esperarFimDaPartida(jogo);
}

async function esperarFimDaPartida(jogo) {
  while (estado.jogando) {
    await new Promise((r) => setTimeout(r, 1500));
    try {
      estado.jogando = (await api("/api/estado")).jogando;
    } catch {
      // o servidor pode estar ocupado; tenta de novo
    }
  }
  $("#jogando").hidden = true;
  esperarSoltarBotoes();
  if (Date.now() - estado.inicioPartida < 8000) {
    mensagem(`${jogo.nome} fechou logo depois de abrir. No PC, veja o log em ~/AllGames/logs/${jogo.id}.log`);
  }
  await carregar();
  const alvo = document.querySelector(`.visao:not([hidden]) [data-id="${CSS.escape(jogo.id)}"]`);
  focar(alvo || document.querySelector(".visao:not([hidden]) [data-nav]"));
}

// ---------------------------------------------------------------- navegação (setas, controle, toque)

function visivel(elemento) {
  if (elemento.closest("[hidden]")) return false;
  const r = elemento.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
}

function focar(elemento, rolar = true) {
  if (!elemento) return;
  estado.focado?.classList.remove("foco");
  estado.focado = elemento;
  elemento.classList.add("foco");
  elemento.focus({ preventScroll: true });
  if (rolar) elemento.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
}

function mover(direcao) {
  const raiz = camadaAberta() || document;
  const itens = [...raiz.querySelectorAll("[data-nav]")].filter(visivel);
  if (!itens.length) return;
  if (!estado.focado || !itens.includes(estado.focado)) return focar(itens[0]);
  const a = estado.focado.getBoundingClientRect();
  const ax = a.left + a.width / 2;
  const ay = a.top + a.height / 2;
  let melhor = null;
  let menor = Infinity;
  for (const item of itens) {
    if (item === estado.focado) continue;
    const b = item.getBoundingClientRect();
    const dx = b.left + b.width / 2 - ax;
    const dy = b.top + b.height / 2 - ay;
    let pontos;
    if (direcao === "direita") pontos = dx > 4 ? dx + Math.abs(dy) * 3 : Infinity;
    else if (direcao === "esquerda") pontos = dx < -4 ? -dx + Math.abs(dy) * 3 : Infinity;
    else if (direcao === "baixo") pontos = dy > 4 ? dy + Math.abs(dx) * 0.6 : Infinity;
    else pontos = dy < -4 ? -dy + Math.abs(dx) * 0.6 : Infinity;
    if (pontos < menor) {
      menor = pontos;
      melhor = item;
    }
  }
  if (melhor) focar(melhor);
  else if (direcao === "cima" && !camadaAberta()) window.scrollTo({ top: 0, behavior: "smooth" });
}

function acao(nome) {
  if (estado.jogando) return;
  if (nome === "a") estado.focado?.click();
  else if (nome === "b") camadaAberta() ? fecharCamada() : estado.aba !== "inicio" && trocarAba("inicio");
  else if (nome === "lb" || nome === "rb") {
    const abas = ["inicio", "recentes", "instalados", "biblioteca", "downloads"];
    const i = abas.indexOf(estado.aba) + (nome === "rb" ? 1 : -1);
    trocarAba(abas[(i + abas.length) % abas.length]);
  }
  else mover(nome);
}

document.addEventListener("keydown", (evento) => {
  if (evento.target.matches?.("input")) {
    if (evento.key === "Escape" || evento.key === "ArrowDown" || evento.key === "Enter") {
      evento.preventDefault();
      evento.target.blur();
      if (evento.key !== "Escape") mover("baixo");
    }
    return;
  }
  const teclas = { ArrowUp: "cima", ArrowDown: "baixo", ArrowLeft: "esquerda", ArrowRight: "direita", Enter: "a", Escape: "b", Backspace: "b" };
  const nome = teclas[evento.key];
  if (!nome) return;
  evento.preventDefault();
  acao(nome);
});

document.addEventListener("pointerdown", (evento) => {
  const alvo = evento.target.closest("[data-nav]");
  if (alvo) focar(alvo, false);
});

document.addEventListener("click", (evento) => {
  const camada = evento.target.classList?.contains("camada") ? evento.target : null;
  if (camada) fecharCamada(camada);
  const aba = evento.target.closest("[data-aba]");
  if (aba) trocarAba(aba.dataset.aba);
});

// Controle: lê o Gamepad API a cada quadro, com repetição ao segurar a direção.
const botoesAnteriores = {};

function esperarSoltarBotoes() {
  for (const nome of Object.keys(botoesAnteriores)) botoesAnteriores[nome] = { apertado: true, proximo: Infinity };
}

function lerControles(agora) {
  const controles = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
  if (controles.length && !estado.temControle) definirControle(true);
  const pad = controles[0];
  // Com um jogo aberto por cima, o portal ignora o controle para não reagir aos botões do jogo.
  if (pad && document.hasFocus() && !estado.jogando) {
    const [x = 0, y = 0] = pad.axes;
    const b = (i) => Boolean(pad.buttons[i]?.pressed);
    const leitura = {
      cima: b(12) || y < -0.5,
      baixo: b(13) || y > 0.5,
      esquerda: b(14) || x < -0.5,
      direita: b(15) || x > 0.5,
      a: b(0),
      b: b(1),
      lb: b(4),
      rb: b(5),
    };
    for (const [nome, apertado] of Object.entries(leitura)) {
      const anterior = botoesAnteriores[nome] || { apertado: false, proximo: 0 };
      const repete = ["cima", "baixo", "esquerda", "direita"].includes(nome);
      if (apertado && (!anterior.apertado || (repete && agora >= anterior.proximo))) {
        acao(nome);
        anterior.proximo = agora + (anterior.apertado ? 130 : 380);
      }
      if (!apertado) anterior.proximo = 0;
      anterior.apertado = apertado;
      botoesAnteriores[nome] = anterior;
    }
  }
  requestAnimationFrame(lerControles);
}

function definirControle(conectado) {
  estado.temControle = conectado;
  const pilula = $("#entrada");
  pilula.innerHTML = conectado ? `${ICONES.controle} Controle conectado` : `${ICONES.toque} Toque`;
  pilula.classList.toggle("ativo", conectado);
  $("#dica").hidden = !conectado;
  // Se o aviso "precisa de controle" estiver aberto, segue para o jogo.
  const aviso = $("#aviso");
  if (conectado && !aviso.hidden) {
    const jogo = estado.jogos.find((j) => j.id === $(".painel-aviso", aviso)?.dataset.jogo);
    aviso.hidden = true;
    esperarSoltarBotoes();
    if (jogo) jogar(jogo, true);
  }
}

window.addEventListener("gamepadconnected", () => definirControle(true));
window.addEventListener("gamepaddisconnected", () => {
  const restantes = [...(navigator.getGamepads?.() || [])].filter(Boolean);
  definirControle(restantes.length > 0);
});

// ---------------------------------------------------------------- downloads e disco

function formatarBytes(valor) {
  if (valor == null) return "—";
  const unidades = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (valor >= 1024 && i < unidades.length - 1) {
    valor /= 1024;
    i += 1;
  }
  return `${valor.toFixed(valor >= 100 || i === 0 ? 0 : 1).replace(".", ",")} ${unidades[i]}`;
}

function formatarTempo(segundos) {
  if (!segundos) return "";
  const horas = Math.floor(segundos / 3600);
  const minutos = Math.max(1, Math.floor((segundos % 3600) / 60));
  return horas ? `faltam ${horas} h ${minutos} min` : `faltam ${minutos} min`;
}

const NOMES_ESTADO = { baixando: "Baixando", pausado: "Pausado", "na fila": "Na fila", erro: "Erro", concluido: "Concluído" };
const NOMES_ACAO = { pausar: "Pausar", continuar: "Continuar", cancelar: "Parar", abrir_steam: "Abrir downloads da Steam" };

let temporizadorDownloads;
async function carregarDownloads() {
  clearTimeout(temporizadorDownloads);
  let dados;
  try {
    dados = await api("/api/downloads");
  } catch (erro) {
    mensagem(`Não consegui ler os downloads: ${erro.message}`);
    return;
  }
  $("#discos").replaceChildren(
    ...dados.discos.map((d) => {
      const usado = 100 - Math.round((100 * d.livre) / d.total);
      return el(
        "div",
        { class: `disco${d.livre < 20 * 1024 ** 3 ? " disco-cheio" : ""}` },
        el("div", { class: "disco-topo" }, el("b", {}, d.nomes.join(", ")), el("span", {}, `${formatarBytes(d.livre)} livres de ${formatarBytes(d.total)}`)),
        el("div", { class: "barra" }, el("span", { style: `width:${usado}%` })),
        el("small", {}, d.caminho),
      );
    }),
  );
  const lista = dados.downloads;
  $("#lista-downloads").replaceChildren(
    ...(lista.length
      ? lista.map((d) => {
          const progresso = d.total ? Math.round((100 * d.baixado) / d.total) : 0;
          const detalhes = [
            d.total ? `${formatarBytes(d.baixado)} de ${formatarBytes(d.total)}` : null,
            d.velocidade ? `${formatarBytes(d.velocidade)}/s` : null,
            formatarTempo(d.restante),
          ].filter(Boolean);
          return el(
            "div",
            { class: `download estado-${d.estado.replace(" ", "-")}` },
            el("div", { class: "download-topo" }, el("b", {}, d.nome), el("span", { class: "pilula" }, `${d.loja} · ${NOMES_ESTADO[d.estado] || d.estado}`)),
            el("div", { class: "barra" }, el("span", { style: `width:${progresso}%` })),
            el("p", {}, `${progresso}%`, detalhes.length ? ` · ${detalhes.join(" · ")}` : ""),
            d.cabe ? null : el("p", { class: "alerta" }, `Não cabe: faltam ${formatarBytes(d.total - d.baixado)} e o disco tem ${formatarBytes(d.livre)} livres.`),
            d.erro ? el("p", { class: "alerta" }, d.erro) : null,
            el(
              "div",
              { class: "acoes" },
              d.acoes.map((acao) =>
                el("button", { class: `botao${acao === "cancelar" ? " perigo" : ""}`, "data-nav": true, onclick: () => acaoDownload(d, acao) }, NOMES_ACAO[acao] || acao),
              ),
            ),
          );
        })
      : [el("p", { class: "vazio" }, "Nenhum download agora. Instale um jogo da Steam ou da Epic pela Biblioteca.")]),
  );
  if (estado.aba === "downloads") temporizadorDownloads = setTimeout(carregarDownloads, 2000);
}

function acaoDownload(download, acao) {
  api(`/api/download?id=${encodeURIComponent(download.id)}&acao=${acao}`, "POST")
    .then(() => {
      if (acao === "abrir_steam") mensagem("A tela de downloads da Steam abriu: lá dá para pausar e retomar.");
      return carregarDownloads();
    })
    .catch((erro) => mensagem(`Não deu: ${erro.message}`));
}

// ---------------------------------------------------------------- início

$("#busca").addEventListener("input", (evento) => {
  estado.busca = evento.target.value;
  estado.limiteGrade = 0;
  renderizarBiblioteca();
});
// Com o controle, "A" na busca abre o teclado (o do Moonlight, no celular).
$("#busca").addEventListener("click", (evento) => evento.target.focus());

// A Steam abre em tela cheia (Big Picture), como no botão Guide do controle.
// Para voltar: segure Select + Start.
$("#abrir-steam").addEventListener("click", () => {
  api("/api/steam", "POST")
    .then(() => mensagem("Abrindo a Steam. Para voltar ao AllGames, segure Select + Start."))
    .catch((erro) => mensagem(`Não deu: ${erro.message}`));
});

$("#sair").addEventListener("click", () => {
  api("/api/sair", "POST").catch(() => {});
  document.body.classList.add("saindo");
});

function relogio() {
  $("#relogio").textContent = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

let temporizadorTarefas;
async function carregar() {
  try {
    const dados = await api("/api/jogos");
    estado.jogos = dados.jogos;
    estado.versao = dados.versao;
    estado.podeSair = dados.pode_sair;
    const contagem = $("#contagem-downloads");
    contagem.hidden = !dados.downloads_ativos;
    contagem.textContent = dados.downloads_ativos || "";
    renderizar();
    clearTimeout(temporizadorTarefas);
    const ocupado = estado.jogos.some((j) => j.tarefa === "instalando") || dados.downloads_ativos;
    if (ocupado) temporizadorTarefas = setTimeout(carregar, ocupado && estado.aba === "inicio" ? 5000 : 3000);
    if (dados.jogando && !estado.jogando) {
      const jogo = estado.jogos.find((j) => j.id === dados.jogando);
      if (jogo) mostrarJogando(jogo);
    }
  } catch (erro) {
    mensagem(`Não consegui falar com o AllGames no PC: ${erro.message}`);
  }
}

// Jogo novo copiado para a pasta aparece sozinho: a cada 15 s o portal confere se as pastas
// mudaram (uma conta rápida no PC) e só então recarrega a lista. Não confere durante o jogo.
setInterval(async () => {
  if (estado.jogando || document.hidden || camadaAberta()) return;
  try {
    const { versao } = await api("/api/versao");
    if (estado.versao && versao !== estado.versao) await carregar();
  } catch {
    // o PC pode estar ocupado; confere de novo daqui a pouco
  }
}, 15000);

definirControle(false);
relogio();
setInterval(relogio, 15000);
carregar().then(() => focar(document.querySelector("#destaque [data-nav]") || document.querySelector("[data-nav]"), false));
requestAnimationFrame(lerControles);
