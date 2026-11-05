# Deploy do Worker (grátis, ~5 min)

1. Crie conta grátis em https://dash.cloudflare.com/sign-up (sem cartão).
2. Menu **Workers & Pages** → **Create** → **Create Worker** → nome `taste-memory` → **Deploy**.
3. Clique em **Edit code**, apague o conteúdo e cole o arquivo `worker.js` desta pasta. **Deploy**.
4. Copie a URL (`https://taste-memory.<sua-conta>.workers.dev`).
5. No app, cole essa URL em **Configurações → URL do Worker** e toque em **Sincronizar**.

Se o seu Pages não for `https://rpten.github.io`, troque `ALLOWED_ORIGINS` no topo do código.
O Worker só aceita as duas rotas (`/letterboxd`, `/goodreads`) e valida os parâmetros; não guarda nada.
