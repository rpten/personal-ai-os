slug: taste-memory

Decisão de Rafael (05/11), substitui a `pending_task` atual:

**v1.1 — indicações argumentadas + chat, com a chave só no servidor (Cloudflare Worker).**

Produto:
1. Cada indicação mostra uma sinopse curta e "por que você gostaria", citando itens e notas reais do histórico dele.
2. Cada indicação tem um chat: ele pode perguntar, discordar e pedir alternativas; o LLM responde com o contexto do gosto dele e da indicação. O feedback (já vi/quero/não curto) continua.

Arquitetura (decidida por ele, não pergunte de novo):
- Worker `taste-memory-recs` na Cloudflare, plano grátis, com `GEMINI_API_KEY` como segredo do Worker. CORS só para https://rpten.github.io. O app nunca vê a chave; remova o campo de chave e qualquer resto dela no localStorage.
- Coleta do Letterboxd continua na workflow `sync` (sem mudança).

Execução:
- Trabalhe já: implemente app + Worker num marco M4 (branch `factory/taste-memory/m4`), com testes e QA contra um Worker simulado.
- Se os segredos `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` e `GEMINI_API_KEY` existirem: faça o deploy, teste o chat de verdade e inclua a evidência real no PR.
- Se faltarem: abra o PR mesmo assim, deixe claro que o deploy e o teste real estão pendentes, e guarde em `state.pending_task` só "deploy do Worker + teste real do M4". O passo a passo dos segredos já foi postado na issue #3; não repita, apenas aponte para ele.
- Status do projeto volta para `awaiting_milestone_approval` com o M4.
