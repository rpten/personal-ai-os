# Personal AI OS — Fábrica de projetos

Você abre uma issue com uma ideia. Um agente (Claude Code rodando no GitHub Actions) te entrevista com perguntas clicáveis, propõe o plano, constrói marco a marco, testa, te mostra evidências num PR e publica o app. Você só marca caixas, mergeia PRs e aplica labels, tudo pelo app do GitHub no celular.

## Como funciona

| Peça | Papel |
|---|---|
| Este repositório | Fonte da verdade: protocolo, estado e código de todos os projetos |
| Issue | Uma ideia/projeto e o canal de conversa com o agente |
| Caixas `- [ ]` nos comentários | Botões: respostas do discovery e aprovações |
| PR | Um marco, com evidências de QA. Mergear = aprovar |
| Labels | `aprovado`, `pausado`, `retomar`, `encerrado`, `fila`, `fabrica` |
| `.github/workflows/factory.yml` | O "worker": acorda o agente a cada ação sua |
| `factory/scripts/guard.py` | Regras fixas: só você aciona, limite de WIP, ignora ruído |
| `CLAUDE.md` | Protocolo que o agente segue (discovery, marcos, QA, limites) |
| GitHub Pages | Painel de projetos + apps publicados em `/<slug>/` |
| App GitHub no celular | Interface e notificações |

Sem servidor próprio, sem banco, sem segundo app para manter.

## Uso diário

1. **Nova ideia:** abra qualquer issue (ou use "➕ Nova ideia" no painel). Escreva poucas linhas. Sem labels.
2. **Discovery:** responda marcando uma caixa em cada pergunta (ou comente, se for "Outro").
3. **Plano:** marque "Aprovar" (ou aplique o label `aprovado`).
4. **Marcos:** veja os prints no PR e mergeie. Para ajustes, marque "Pedir ajuste" e comente.
5. **Painel:** https://rpten.github.io/personal-ai-os/.

Limite padrão: 1 projeto ativo (`factory/config.json`). Ideias extras entram na fila e começam sozinhas.

Nada fica parado em silêncio:
- 👀 na sua issue/comentário = a fábrica está executando; 🚀 = terminou; 😕 = falhou (com comentário explicando e nova tentativa automática).
- Toda execução só fica verde se o trabalho foi registrado no estado do projeto; quando o guard decide não executar, o job do agente aparece como pulado e o motivo fica no histórico.
- A cada hora (e a cada mudança no repo) a fábrica retoma ideias não iniciadas, instruções da caixa de entrada e ações suas que se perderam.
- Painel: o que precisa de você, estado de cada projeto e histórico em linguagem humana.

## Configuração única

1. Repositório `personal-ai-os` com este conteúdo.
2. Segredo `CLAUDE_CODE_OAUTH_TOKEN` (Settings → Secrets and variables → Actions). Gere uma vez num computador com `claude setup-token`. Usa sua assinatura do Claude, sem cobrança por API. Alternativa: `ANTHROPIC_API_KEY` do Console (cobrança por uso).
3. Settings → Actions → General → Workflow permissions: **Read and write** e **Allow GitHub Actions to create and approve pull requests**.
4. Settings → Pages → Source: **GitHub Actions**.
5. App do GitHub no celular, com notificações do repositório ativadas.

## Controles de segurança e custo

- Só o dono do repositório aciona o agente (checado na workflow e no guard).
- Uma execução por vez; cada uma limitada a 100 minutos e 200 turnos.
- O agente não altera a própria fábrica fora de issues `fabrica`, não usa serviços pagos e transforma ações irreversíveis em perguntas.
- Nenhum segredo fica no repositório.

## ChatGPT e Codex

Leem o mesmo repositório (conector do GitHub). `AGENTS.md` aponta para o mesmo protocolo. Revisões entram como comentário no PR, no mesmo histórico, sem copiar nada entre ferramentas.
