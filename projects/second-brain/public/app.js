(function () {
  var form = document.getElementById("form"), campos = document.getElementById("campos"),
      saida = document.getElementById("saida"), texto = document.getElementById("texto"),
      erro = document.getElementById("erro");
  var todas = [{ id: "ideia", rotulo: "Qual é a sua ideia?", dica: "Ex.: um app para organizar minhas leituras" }].concat(Plano.PERGUNTAS);
  todas.forEach(function (p, i) {
    var l = document.createElement("label");
    l.setAttribute("for", p.id);
    l.textContent = (i === 0 ? "" : i + ". ") + p.rotulo;
    var t = document.createElement("textarea");
    t.id = p.id; t.name = p.id; t.rows = 2; t.placeholder = p.dica;
    campos.appendChild(l); campos.appendChild(t);
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var entrada = {};
    todas.forEach(function (p) { entrada[p.id] = document.getElementById(p.id).value; });
    try {
      var plano = Plano.gerarPlano(entrada);
      erro.hidden = true; texto.textContent = plano.texto; saida.hidden = false;
      saida.scrollIntoView({ behavior: "smooth" });
    } catch (x) {
      saida.hidden = true; erro.textContent = x.message; erro.hidden = false;
    }
  });
})();
