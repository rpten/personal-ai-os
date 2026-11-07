slug: taste-memory

Decisão de Rafael (07/11): **redesign substancial do Taste Memory**, piloto da Design Capability v1. Não é ajuste cosmético.

Como fazer: carregue a skill `fabrica-design` e siga os 8 passos. Este é o marco **M7** (branch `factory/taste-memory/m7`).

Dependência: se o PR #10 (M6, backlog) ainda estiver aberto, crie o branch do M7 a partir de `origin/factory/taste-memory/m6` (o redesign precisa incluir o backlog) e diga no PR, logo no início, "Depende do #10: mergeie o #10 antes". Se já estiver mergeado, parta de `main`.

Prioridades de Rafael, em ordem:
1. Hierarquia das recomendações (é o coração do app).
2. Apresentação dos filmes/livros e das informações (sinopse, por que você gostaria, referências do seu histórico).
3. Experiência do chat por indicação.
4. Navegação (hoje é uma página única com 6 blocos empilhados).
5. Layout no celular (uso principal).
6. Tipografia, espaçamento e acabamento.
7. Estados de carregamento, erro, vazio e feedback das ações.

Ponto de partida (auditoria preliminar feita pela fábrica; refaça a sua com prints):
- Celular: página única de ~9 telas, sem navegação. A ação principal ("Me indique 5") só aparece no 2º bloco, abaixo de estatísticas.
- Abas Filmes/Livros duplicadas: no topo e de novo dentro do backlog.
- Cada indicação tem 4 botões do mesmo peso (Já vi / Quero / Não curto / Conversar). Título pequeno, sem capa, rótulo "POR QUE VOCÊ GOSTARIA" em caixa alta pequena.
- Resumo: barras de 8px, listas com marcadores, datas cruas ("2019-03-02"), média "4.25" com ponto.
- Funções administrativas (atualizar, importar CSV, backup) ocupam o mesmo peso visual que o conteúdo; `input file` nativo mostra "Choose File" em inglês.
- Tipografia `system-ui`, paleta escura azul genérica, emoji como ícone (🎬 📚 💬).
- Mensagens de status soltas ("Pronto: 3 indicações em 0s").

Regras:
- Preserve toda a funcionalidade (sincronização, CSV, indicações, chat, feedback, backlog, nota, backup). Não altere lógica de negócio nem o Worker sem necessidade. Os testes existentes (`app/test`, `worker/test.mjs`) e um QA funcional do fluxo principal precisam continuar verdes.
- Capas: se usar imagens externas, só de fonte gratuita e sem chave, com placeholder desenhado quando não houver. Senão, um tratamento tipográfico forte.
- Registre a direção (brief, direção, UX e problemas) em `design/brief.md` no **primeiro commit** do branch, antes do código.
- `design/flows.json` precisa cobrir: primeiro acesso (sem dados), com dados, indicações carregando, indicações prontas, chat aberto, erro do Worker, backlog e importação. Worker simulado via `routes`.
- PR `[taste-memory] M7: Redesign`, com QA funcional e QA visual separados, prints de antes e depois no celular, e `design-review.md`.
- Ao terminar: o marco M7 fica `awaiting_approval` no estado e `next_action` pede a Rafael para olhar os prints e mergear (respeitando a ordem do #10).
