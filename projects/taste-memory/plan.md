# Memória de gosto + recomendações — Plano

Stack: HTML/JS estático (Vite opcional) em `public/`; chamadas diretas à API do Gemini pelo navegador; dados em localStorage/IndexedDB. Simples e publica no GitHub Pages.

| Marco | Entrega | Critério de pronto | Evidência esperada |
|---|---|---|---|
| M1 | Importar CSV Letterboxd/Goodreads, guardar no navegador, tela de resumo do gosto | CSVs de exemplo importam; contagem e notas corretas; persiste após recarregar | Testes do parser + prints (celular e desktop) |
| M2 | Pedido de recomendação: filme/livro, humor opcional, chave Gemini, 5 sugestões com justificativa | Prompt montado com as notas; resposta parseada e exibida; erros tratados (chave inválida, cota) | Testes com API simulada + prints |
| M3 | Feedback já vi/li, quero, não curto + exportar/importar backup | Marcações persistem, mudam o próximo pedido e excluem repetidas; backup restaura | Testes + prints |

Riscos / bloqueios previstos:
- Teste real com Gemini exige a chave de Rafael: QA usará API simulada; validação real fica com ele.
- Cota/limites do plano gratuito do Gemini.
- Sugestões podem inventar títulos; mitigação: pedir saída estruturada e mostrar ano/autor.
