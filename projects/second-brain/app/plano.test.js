const test = require("node:test");
const assert = require("node:assert");
const { gerarPlano, validar, PERGUNTAS } = require("../public/plano.js");

const base = {
  ideia: "um app para organizar minhas leituras",
  usuario: "eu mesmo, no celular",
  dor: "esqueço o que li",
  fluxo: "abro, adiciono um livro, marco como lido",
  pronto: "uso sem ajuda em 2 minutos",
  fora: "login; sincronização, recomendações"
};

test("são 5 perguntas", () => assert.strictEqual(PERGUNTAS.length, 5));

test("plano tem todas as seções", () => {
  const t = gerarPlano(base).texto;
  for (const s of ["## Resumo", "## Menor versão útil", "## Marcos", "## Próximo passo", "## Riscos", "## Backlog", "## Checklist de pronto"])
    assert.ok(t.includes(s), s);
});

test("3 marcos, último usa o critério de pronto", () => {
  const p = gerarPlano(base);
  assert.strictEqual(p.marcos.length, 3);
  assert.strictEqual(p.marcos[2].pronto, "uso sem ajuda em 2 minutos");
});

test("backlog vem do que fica de fora", () => {
  assert.deepStrictEqual(gerarPlano(base).backlog, ["login", "sincronização", "recomendações"]);
});

test("riscos detectam login e sincronização, e sempre há riscos genéricos", () => {
  const r = gerarPlano(base).riscos.join(" ");
  assert.match(r, /Login/);
  assert.match(r, /sincroniza/i);
  assert.ok(gerarPlano({ ...base, fora: "nada" }).riscos.length >= 2);
});

test("resposta vazia é rejeitada", () => {
  assert.deepStrictEqual(validar({ ...base, dor: "  " }), ["dor"]);
  assert.throws(() => gerarPlano({ ...base, ideia: "" }), /ideia/);
});

test("é determinístico", () => assert.strictEqual(gerarPlano(base).texto, gerarPlano(base).texto));
