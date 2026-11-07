# Auditoria — repositório vs. Blueprint v1

*06/11/2026 (P0) · atualizado em 07/11/2026 (Design Capability v1) · base: `docs/blueprint.md`.*

Legenda: ✅ implementado · 🟡 parcial · ⬜ ausente · ⚠️ contraditório (encontrado e corrigido nesta rodada, salvo indicação).

## Mapa de nomes

| Blueprint | No repositório |
|---|---|
| Jarvis | Issues do GitHub: captura, discovery com caixas clicáveis, aprovações (`CLAUDE.md` §3–4) |
| Command Center | Painel no GitHub Pages (`factory/scripts/build_site.py`) |
| Construtora | Workflow `factory` (guard → agente Claude Code → verificador) + `sync` + `pages` |
| Context & Memory | — (ausente) |
| Applications | `projects/<slug>/` com estado, código, evidências e publicação próprios |
| Shared Foundation | `factory/` (schema, ledger, scripts, config), `CLAUDE.md`, `docs/` |

## 1. Inconsistências encontradas

| # | Problema | Evidência | Situação |
|---|---|---|---|
| 1 | ⚠️ Eventos podiam ser **descartados em silêncio**: um único grupo de concorrência faz o GitHub cancelar execuções pendentes além de uma | `factory.yml` (antes): `concurrency: group: factory` | Corrigido: grupo por projeto + retomada automática de ações posteriores ao último evento |
| 2 | ⚠️ **Verde ≠ trabalho feito**: o job ficava verde quando o guard pulava e quando o agente saía sem fazer nada | `factory.yml` (antes): job único; `verify.py` só checava ideia nova | Corrigido: job do agente aparece como pulado; verde exige `last_event.run_id` desta execução em `main` |
| 3 | ⚠️ Promessa falsa: o aviso de falha dizia que "a próxima reconciliação tenta de novo", mas só ideias novas eram retentadas | `verify.py` (antes) | Corrigido: reconciliação retoma projetos com atividade não atendida, até 3 falhas seguidas |
| 4 | ⚠️ Estado fora do schema passava despercebido (marco com status `in_review`) | `projects/taste-memory/state.json` (antes) | Corrigido: verificador valida schema e transições; teste de regressão cobre os estados reais |
| 5 | ⚠️ Commits horários sem conteúdo novo (só o carimbo `updated.txt`) poluíam o histórico | `git diff 481bffb 11285e2` | Corrigido em `sync.yml` |
| 6 | ⚠️ Próxima ação do taste-memory mandava mergear o PR #7 antes do deploy do Worker, o que quebraria o app publicado | `state.next_action` | Enviado ao agente pela caixa de entrada (também serve de teste ponta a ponta do P0) |
| 7 | 🟡 Ignorados sem registro: não havia histórico de eventos nem motivo visível | — | Corrigido: ledger `factory/events/*.jsonl` + resumo da execução + comentário quando a intenção de Rafael não pôde ser atendida |
| 8 | 🟡 Branch `diagnostics` cresce sem limite | `factory.yml`, passo "Salvar diagnóstico" | Pendente (baixo impacto) |
| 9 | 🟡 Labels `discovery`/`proj:<slug>` nunca são removidos ao mudar de fase | issues #1, #3 | Pendente (cosmético) |

## 2. Seção a seção

### §2 Princípios
| Princípio | | Evidência |
|---|---|---|
| Direção humana; execução autônoma | ✅ | `CLAUDE.md` §3; taste-memory entregue só com cliques |
| Uma fonte de verdade | ✅ | `state.json` (projeto) + ledger (eventos) + `docs/` (arquitetura). A thread da issue é conversa, não estado |
| Conversa e dashboard complementares | 🟡 | Issues + painel; sem interface conversacional própria (P3) |
| QA/diagnóstico/correção automatizados | 🟡 | Agente testa e faz prints; diagnóstico salvo em falha; retentativa automática. A fábrica não confere se o PR traz evidência |
| Interromper só por decisão real | 🟡 | Protocolo exige; histórico mostra o agente pedindo deploy manual antes da regra §8 |
| Toda execução termina em entrega, bloqueio ou pedido | ✅ | `verify.py`: done / waiting / blocked / failed, sempre com `next_action` |
| Construtora separada das aplicações | 🟡 | Separadas por pasta, estado e URL; mesmo repositório |

### §4–5 Componentes e fluxo
| Item | | Evidência |
|---|---|---|
| Captura e discovery uma pergunta por vez | ✅ | issue #3 (perguntas q1–q5, bloqueios b1–b2) |
| Brief, plano, aprovação | ✅ | `projects/taste-memory/brief.md`, `plan.md`; bloco `kind=plan` |
| Execução por marcos, QA, entrega | ✅ | PRs #4–#6, `evidence/m*/`, entrega v1 |
| Encerramento e parada | ✅ | status `delivered`/`closed`; execução sob demanda |
| Context & Memory | ⬜ | — (P4) |

### §6 Modelo de estado
| Campo | | Evidência |
|---|---|---|
| id, nome, fase, marcos, decisões, links de PR | ✅ | `factory/state.schema.json` |
| Último evento, timestamp, próxima ação | ✅ | `last_event`, `next_action` (obrigatórios, conferidos pelo verificador) |
| Objetivo e owner explícitos | 🟡 | objetivo em `brief.md`; owner implícito (Rafael) |
| Dependências entre marcos | ⬜ | marcos são sequenciais |

### §7 Acionamento e confiabilidade
| Requisito | | Evidência |
|---|---|---|
| Ideia pelo fluxo natural sem label | ✅ | `guard.py`; teste `test_issue_sem_label_vira_ideia`; validado na issue #3 |
| Ignorado com explicação visível | ✅ | ledger + resumo da execução + comentário quando aplicável |
| Verde ≠ trabalho falso | ✅ | jobs separados; `verify.py` |
| Estados distintos | ✅ | 👀 executando · ledger: `ignored`, `queued`, `done`, `waiting`, `blocked`, `failed` |
| Idempotência / sem duplicação | ✅ | chave por evento no ledger; concorrência por projeto |
| Testes de gatilhos, guardas e transições | ✅ | `factory/tests/` (49 testes) em `test.yml` a cada mudança |
| Regressão e rollback | 🟡 | CI de regressão + ponto de restauração no branch `release/factory-v1`; rollback = `git revert`. Sem proteção de branch (exige configuração de Rafael) |
| Autorização para ações pagas/irreversíveis | 🟡 | regra no protocolo; barreira técnica só em `.github/` |
| Sob demanda; agentes param | ✅ | cada execução termina e o job encerra |

### §8 QA e evidências — 🟡
Testes, prints, console e limitações estão em todos os PRs de marco. **Interface:** o verificador agora exige brief/direção/UX, `flows.json` e `design-review.md`, e roda o QA visual de novo no branch do PR (0 bloqueantes). **Lógica não visual:** a fábrica ainda não confere se o PR traz testes.

### §8.1 Design Capability — ✅ (v1)
| Requisito | | Evidência |
|---|---|---|
| Skills auditadas e versionadas | ✅ | `.claude/skills/{frontend-design,ui-ux-pro-max}`, `factory/design/vendor.json`, teste de integridade |
| Acionada automaticamente | ✅ | descrição da skill `fabrica-design` + `CLAUDE.md` §3 + portão no `verify.py`; uso registrado no ledger |
| Workflow de 8 passos | ✅ | `.claude/skills/fabrica-design/SKILL.md`, modelos em `factory/templates/` |
| QA visual automatizado | ✅ | `factory/scripts/visual_qa.py` (3 testes com páginas boas/ruins), portão em `verify.py` (6 testes) |
| Julgamento estético | 🟡 | inspeção dos prints pelo agente, registrada e exigida; não é medida automaticamente |
| Design system por produto | ✅ | `foundation.css` compartilhada + `tokens.css` por app |
| Piloto (Taste Memory) | ver relatório do PR do redesign | |

### §9 Command Center — 🟡
Agora tem: totais, **Preciso de você**, cartão por projeto (fase, marcos, último evento, próxima ação), entregas (link do app) e histórico em linguagem humana com falhas. Falta: objetivo no cartão, ações rápidas além de "Nova ideia", releases.

### §10 Roadmap
| Fase | |
|---|---|
| P0 Confiabilidade e fonte de verdade | ✅ esta entrega |
| P1 Ciclo de projeto | ✅ validado com taste-memory |
| P2 Command Center | 🟡 |
| Design Capability v1 | ✅ capacidade; piloto no Taste Memory em andamento |
| P3 Jarvis integrado | ⬜ |
| P4 Context & Memory | ⬜ |
| P5 Aplicações | 🟡 taste-memory v1 entregue, M4 em andamento |

## 3. Próximos passos (por dependência)

1. **P0 — fechar:** validar em produção (instrução real pela caixa de entrada); se Rafael quiser, proteção da branch `main` exigindo o check `test`.
2. **P1/§8:** o verificador passa a exigir evidência nos PRs de marco (seção de testes + prints).
3. **P2:** objetivo e ações rápidas nos cartões; podar o branch `diagnostics`.
4. **P3:** interface conversacional sobre o mesmo estado (decisão de produto de Rafael).
5. **P4:** Context & Memory (decisão de produto de Rafael).
