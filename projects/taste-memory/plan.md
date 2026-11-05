# Memória de gosto + recomendações — Plano

Stack: HTML/JS estático em `public/` (GitHub Pages); Cloudflare Worker grátis (código em `app/worker/`) que busca os RSS públicos (Letterboxd `rafaeldez`, Goodreads `196111676`) e devolve ao app; chamadas diretas ao Gemini pelo navegador; dados em localStorage/IndexedDB.

| Marco | Entrega | Critério de pronto | Evidência esperada |
|---|---|---|---|
| M1 | Sincronização RSS (Worker + app) + importação única de CSV para histórico + resumo do gosto | Parsers de RSS/CSV testados com amostras; sync mescla sem duplicar; persiste após recarregar; passo a passo de deploy do Worker | Testes + prints (celular e desktop) |
| M2 | Pedido de recomendação: filme/livro, humor opcional, chave Gemini, 5 sugestões com justificativa | Prompt montado com as notas; resposta parseada e exibida; erros tratados (chave inválida, cota) | Testes com API simulada + prints |
| M3 | Feedback já vi/li, quero, não curto + exportar/importar backup | Marcações persistem, mudam o próximo pedido e excluem repetidas; backup restaura | Testes + prints |

Riscos / bloqueios previstos:
- Deploy do Worker exige conta Cloudflare grátis de Rafael (eu não crio contas); sem o deploy, o app usa só CSV até ele publicar. QA usa RSS de exemplo (sem rede garantida).
- RSS do Goodreads é instável e traz poucos itens; fallback é CSV. Letterboxd traz só ~50 atividades recentes.
- Teste real com Gemini exige a chave de Rafael: QA usará API simulada; validação real fica com ele.
- Cota/limites do plano gratuito do Gemini.
- Sugestões podem inventar títulos; mitigação: pedir saída estruturada e mostrar ano/autor.
