# Memória de gosto + recomendações — Brief

- **Problema:** Não saber o que assistir/ler agora, apesar de anos de histórico e notas espalhados em Letterboxd e Goodreads.
- **Para quem / quando uso:** Rafael, no celular ou desktop, na hora de escolher um filme ou livro.
- **Caso de uso de ponta a ponta (v1):** Importa o CSV do Letterboxd e/ou Goodreads → escolhe filme ou livro → (opcional) digita humor/contexto → recebe 5 sugestões novas com justificativa baseada nas suas notas → marca cada uma como "já vi/li", "quero" ou "não curto", e isso entra no gosto para os próximos pedidos.
- **Definição de pronto:** Fluxo acima funcionando no site publicado, com Gemini free tier (chave só no navegador), dados só no navegador (localStorage/IndexedDB), sem servidor.
- **Fora da v1:** YouTube e outras fontes; projetos de idiomas; contas/sincronização entre dispositivos.
- **Decisões tomadas no discovery:** IA com Gemini free tier; chave e dados só no navegador; CSV Letterboxd + Goodreads; 5 sugestões com humor opcional; feedback "já vi/li / quero / não curto".
