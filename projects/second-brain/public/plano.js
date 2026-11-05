/* Gerador de plano por regras (sem IA, sem rede). Funciona no navegador e no Node. */
(function (root) {
  var PERGUNTAS = [
    { id: "usuario", rotulo: "Quem vai usar?", dica: "Ex.: eu mesmo, no celular, à noite" },
    { id: "dor", rotulo: "Qual problema isso resolve?", dica: "Ex.: perco ideias e nunca saio do papel" },
    { id: "fluxo", rotulo: "Um uso de ponta a ponta: o que a pessoa faz do início ao fim?", dica: "Ex.: abre, digita a ideia, recebe o plano, copia" },
    { id: "pronto", rotulo: "Como você saberá que está pronto?", dica: "Ex.: consigo usar sem ajuda em 2 minutos" },
    { id: "fora", rotulo: "O que fica de fora da primeira versão?", dica: "Ex.: login, sincronização, notificações" }
  ];

  var RISCOS = [
    { re: /\b(login|conta|senha|usu[aá]rios?\s+cadastrad)/i, txt: "Login/contas exigem backend: decidir antes se é mesmo necessário na v1." },
    { re: /\b(pagamento|pagar|cobran[cç]a|assinatura|pix)/i, txt: "Pagamentos envolvem custo e serviço externo: só com decisão explícita." },
    { re: /\b(ia|intelig[eê]ncia artificial|chatgpt|gpt|claude|llm)\b/i, txt: "IA tem custo e imprevisibilidade: começar por regras simples e medir." },
    { re: /\b(integra|api|sincroniz|nuvem|compartilh)/i, txt: "Integrações e sincronização dependem de terceiros: deixar para depois do caso de uso principal." },
    { re: /\b(notifica|lembrete|alerta)/i, txt: "Notificações exigem permissão e serviço de envio: avaliar separado." },
    { re: /\b(celular|mobile|app)\b/i, txt: "Uso no celular: validar tela pequena desde o primeiro marco." }
  ];

  function limpar(t) { return String(t == null ? "" : t).replace(/\s+/g, " ").trim(); }
  function frase(t) { t = limpar(t); return t ? t.replace(/[.\s]+$/, "") : ""; }
  function maiuscula(t) { return t ? t.charAt(0).toUpperCase() + t.slice(1) : t; }
  function itens(t) {
    return String(t || "").split(/\n|;|,|\s+e\s+/i).map(frase).filter(Boolean);
  }

  function validar(entrada) {
    var faltam = [];
    if (!limpar(entrada && entrada.ideia)) faltam.push("ideia");
    PERGUNTAS.forEach(function (p) { if (!limpar(entrada && entrada[p.id])) faltam.push(p.id); });
    return faltam;
  }

  function gerarPlano(entrada) {
    var faltam = validar(entrada);
    if (faltam.length) throw new Error("Faltam respostas: " + faltam.join(", "));
    var ideia = frase(entrada.ideia), usuario = frase(entrada.usuario), dor = frase(entrada.dor),
        fluxo = frase(entrada.fluxo), pronto = frase(entrada.pronto), fora = itens(entrada.fora);
    var todo = [ideia, usuario, dor, fluxo, pronto, entrada.fora].join(" ");

    var riscos = RISCOS.filter(function (r) { return r.re.test(todo); }).map(function (r) { return r.txt; });
    riscos.push("Escopo crescer além do caso de uso principal: tudo que não ajuda “" + fluxo + "” vai para o backlog.");
    riscos.push("Definição de pronto vaga: “" + pronto + "” precisa virar algo que dá para checar.");

    var passo = "Hoje: escreva em uma frase o resultado final do uso de ponta a ponta (“" + fluxo +
      "”) e faça só o primeiro passo dele funcionar, mesmo que feio.";

    var plano = {
      titulo: maiuscula(ideia),
      resumo: maiuscula(ideia) + ". Para " + usuario + ". Resolve: " + dor + ".",
      menorVersao: "Somente o fluxo: " + fluxo + ". Nada além disso na v1.",
      marcos: [
        { n: 1, titulo: "Caso de uso principal funcionando", pronto: "Dá para fazer: " + fluxo },
        { n: 2, titulo: "Guardar o que importa e corrigir o que travou", pronto: "Resultado do M1 persiste e os pontos de atrito do teste real foram resolvidos" },
        { n: 3, titulo: "Acabamento e entrega", pronto: pronto }
      ],
      proximoPasso: passo,
      riscos: riscos,
      backlog: fora.length ? fora : ["(nada definido: revise o que ficou de fora)"],
      checklist: [
        "O fluxo “" + fluxo + "” funciona do início ao fim",
        "Testado por " + usuario + " no uso real",
        "Critério de pronto atendido: " + pronto,
        "Nada do backlog entrou na v1",
        "Riscos revisados e sem bloqueios abertos"
      ]
    };
    plano.texto = paraTexto(plano);
    return plano;
  }

  function lista(arr, num) {
    return arr.map(function (x, i) { return (num ? (i + 1) + ". " : "- ") + x; }).join("\n");
  }

  function paraTexto(p) {
    return [
      "# " + p.titulo, "",
      "## Resumo", p.resumo, "",
      "## Menor versão útil", p.menorVersao, "",
      "## Marcos", p.marcos.map(function (m) { return "M" + m.n + " — " + m.titulo + "\n   Pronto quando: " + m.pronto; }).join("\n"), "",
      "## Próximo passo", p.proximoPasso, "",
      "## Riscos", lista(p.riscos), "",
      "## Backlog (fora da v1)", lista(p.backlog), "",
      "## Checklist de pronto", p.checklist.map(function (x) { return "- [ ] " + x; }).join("\n"), ""
    ].join("\n");
  }

  var api = { PERGUNTAS: PERGUNTAS, validar: validar, gerarPlano: gerarPlano };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Plano = api;
})(typeof window !== "undefined" ? window : this);
