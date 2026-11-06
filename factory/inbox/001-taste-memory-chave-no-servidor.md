slug: taste-memory

Decisão de Rafael (05/11): a chave do Gemini não pode ficar no front-end nem ser colada a cada aparelho. Ele vai configurar uma vez só.

Faça:
1. Mova a chamada ao Gemini para um Cloudflare Worker (`taste-memory-recs`) com a chave como segredo do Worker (`wrangler secret put GEMINI_API_KEY`, valor da variável de ambiente). CORS só para https://rpten.github.io.
2. Remova do app o campo de chave e qualquer leitura/escrita dela no localStorage. O app chama o Worker.
3. Teste o Worker de verdade (deploy + chamada real) e mostre a evidência.
4. Se `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` ou `GEMINI_API_KEY` estiverem vazios, não implemente pela metade: comente na issue #3 exatamente quais faltam e como criar cada um (no máximo 3 passos por segredo, com links: aistudio.google.com/apikey para o Gemini; token Cloudflare com o modelo "Edit Cloudflare Workers"). Copie esta instrução inteira para `state.pending_task`, apague o arquivo da caixa de entrada e termine com `👉 Sua vez:` pedindo que ele comente **pronto** na issue #3 quando tiver preenchido. No próximo comentário dele, retome a `pending_task`.

Isto é um ajuste pós-entrega: abra um PR `[taste-memory] Ajuste: chave no servidor` com evidências, como um marco.
