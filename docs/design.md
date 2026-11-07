# Design Capability v1

Capacidade da Construtora para produzir interfaces visualmente boas de forma consistente, e não só interfaces que funcionam. Versão 1, 07/11/2026.

## 1. Skills selecionadas

| | frontend-design (Anthropic) | ui-ux-pro-max (NextLevelBuilder) |
|---|---|---|
| Origem | `anthropics/claude-plugins-official`, plugin oficial v1.1.1 (o link antigo em `claude-code/plugins` hoje só aponta para lá) | `nextlevelbuilder/ui-ux-pro-max-skill`, v2.15.0 |
| Licença | Apache-2.0 | MIT |
| Manutenção | Mantida pela Anthropic; atualizada em 06/11/2026 | Ativa: 85 commits desde 01/08/2026, releases frequentes |
| Conteúdo | 1 arquivo de instruções; sem scripts | Instruções + `search.py` (Python, só biblioteca padrão) sobre CSVs locais (3,3 MB) |
| Rede, credenciais, permissões | Nenhuma | Nenhuma. O script não faz chamadas de rede e só escreve em disco com `--persist` |
| Compatibilidade | Skill de projeto em `.claude/skills/` | Igual; os caminhos usam `CLAUDE_PLUGIN_ROOT`, que a workflow define como a raiz do repo |
| Papel na fábrica | **Direção visual e identidade**: personalidade, tipografia, paleta, composição, copy, autocrítica | **Regras de UX e acessibilidade**: consulta por domínio (`ux`, `typography`, `color`, `icons`, `stack`) e checklist de entrega |

**Por que as duas.** Elas se complementam com pouca sobreposição. A frontend-design é forte em gosto e em evitar interface genérica, mas não tem base de regras. A pro-max tem 119 regras de UX com prioridade, mas o gerador de design system dela produz direções genéricas. No teste com o Taste Memory, ela sugeriu um padrão de landing page "storytelling" e fonte manuscrita para um app de recomendação. Por isso:

- a identidade vem sempre da frontend-design;
- a pro-max entra só como consulta pontual de regras, e o `--design-system` dela não decide a identidade.

**O que ficou de fora.**
- As 6 skills irmãs do repositório da pro-max (brand, banner-design, slides, design, design-system, ui-styling): fora do escopo ou duplicadas, e a ui-styling empurra Tailwind/shadcn, que seria um framework novo.
- Os testes internos da pro-max.
- Nenhuma dependência paga ou credencial.

Os arquivos vendorizados estão em `.claude/skills/`, sem modificação. Procedência (repositório, commit, licença) e hash de cada arquivo ficam em `factory/design/vendor.json`, e um teste de regressão falha se algum deles mudar. Para atualizar, troque os arquivos, atualize `vendor.json` e rode os testes; isso é uma melhoria da fábrica, que passa por PR.

## 2. O que a Construtora ganhou

| Peça | Arquivo | Função |
|---|---|---|
| Skill interna | `.claude/skills/fabrica-design/SKILL.md` | O workflow obrigatório; diz quando usar cada skill e quais artefatos entregar |
| QA visual | `factory/scripts/visual_qa.py` | Prints reais por fluxo × celular/desktop + checks mensuráveis |
| Portão de design | `factory/scripts/verify.py` (`check_design`) | Confere os artefatos e **roda o QA visual de novo** no branch do PR, sem depender do agente |
| Base técnica | `factory/design/foundation.css` | Reset, foco visível, movimento reduzido, safe areas, escalas de espaço e tipografia |
| Identidade por produto | `factory/design/tokens.template.css` → `public/tokens.css` | Cada app define as próprias cores, fontes e raios |
| Modelos | `factory/templates/design-brief.md`, `design-review.md`, `evidence.md` | Brief/direção/UX, revisão com problemas → correções → revalidação, PR com QA funcional e visual separados |
| Telemetria | ledger (`skills_available`, `skills_used`) | Prova, execução a execução, que as skills foram carregadas e usadas |

**Acionamento automático, em três camadas:**
1. A descrição da skill `fabrica-design` faz o Claude Code carregá-la em tarefas de interface.
2. O protocolo (`CLAUDE.md` §3) a torna obrigatória em todo marco que mexe em interface.
3. O verificador reprova o marco se os artefatos faltarem ou se o QA visual tiver bloqueantes.

Nada disso depende de Rafael mencionar design.

## 3. Workflow (8 passos)

1. **Brief:** público, contexto, objetivo, tarefas e conteúdo real; em redesign, auditoria do existente.
2. **Direção:** frontend-design → paleta nomeada, tipografia, composição com wireframe, o elemento memorável e uma revisão contra o genérico.
3. **UX:** hierarquia, navegação, estados, feedback, responsividade, citando as regras da pro-max consultadas.
4. **Implementação:** `tokens.css` + `foundation.css` + CSS próprio, sem framework novo sem justificativa.
5. **QA visual:** `visual_qa.py` sobre `design/flows.json`, cobrindo cada tela e estado.
6. **Inspeção e correção:** o agente abre cada print e critica como diretor de arte; zera bloqueantes e trata avisos.
7. **Revalidação:** roda de novo e inspeciona os prints novos.
8. **Entrega:** `design-review.md` com antes/depois; o PR separa QA funcional de QA visual.

## 4. QA visual

O que é automático (a cada fluxo, no celular a 390px e no desktop a 1280px):

| Bloqueante | Aviso |
|---|---|
| Rolagem horizontal; elemento saindo da tela | Alvo de toque < 44px |
| Texto < 12px | Texto cortado sem reticências |
| Contraste < 4.5:1 (< 3:1 em texto grande) | Controles sobrepostos |
| Controle sem nome acessível | Linha > ~90 caracteres |
| Imagem quebrada ou sem `alt` | Tipografia padrão do sistema sem escolha deliberada |
| Erro de JavaScript/console | Emoji como ícone; rótulos pequenos em caixa alta |
| Falta de `meta viewport`; fluxo que não executa | Página com mais de 5 telas no celular |
| Recurso HTTP que falhou sem ser simulado | |
| Fim do conteúdo coberto por barra fixa | |

Antes de cada print, o QA espera as animações finitas terminarem (um print no meio de uma animação de entrada mostrava cartões invisíveis). Os fluxos simulam a rede (`routes`) para fotografar estados vazio, carregando (`hold`) e erro sem depender de serviços reais.

**O que não é automático, e por isso é obrigatório no workflow:** hierarquia, composição, ritmo e identidade. Os checks só pegam o que é mensurável: o Taste Memory atual passa com **0 bloqueantes** e ainda assim é visualmente fraco. Esses pontos ficam na inspeção dos prints, registrada no `design-review.md`, que o verificador exige.

## 5. Estratégia de design system

- **Compartilhado (infraestrutura):** `foundation.css` (reset, acessibilidade, movimento, escalas), contrato de nomes de tokens, modelos de documento e o QA visual. Atualizado só como melhoria da fábrica.
- **Por produto (identidade):** `tokens.css` com paleta, fontes e raios, e componentes no CSS do próprio app. Nada impõe uma identidade comum; a skill proíbe copiar a de outro app.
- **Componentes:** cada produto mantém os seus. Quando o mesmo padrão aparecer em 2 apps (ex.: chat, lista com capa, estados vazio/erro), ele vira um padrão documentado em `factory/design/`, como estrutura e não como estética.
- **Acessibilidade e responsividade:** piso garantido pela `foundation.css` e pelos checks bloqueantes.
- **Sem framework:** HTML/CSS/JS puro, coerente com a stack dos apps publicados no Pages. Introduzir um exige justificativa em `state.decisions`.

## 6. Limites conhecidos

- O contraste automático ignora fundos com imagem ou gradiente.
- O julgamento estético depende do modelo inspecionando prints. O portão garante que a inspeção foi registrada, não que ela é boa. A aprovação final do marco continua sendo de Rafael.
- O QA visual roda no Chrome do runner. Não cobre Safari/iOS real.

## 7. Histórico

- **v1.1 (07/11):** espera de animações antes do print; regra "conteúdo coberto por barra fixa"; sobreposição ignora elementos fixos; o job do agente sempre usa o `main` mais recente. Motivação: inspeção independente do piloto do Taste Memory.
