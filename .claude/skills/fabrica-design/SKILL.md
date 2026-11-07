---
name: fabrica-design
description: Workflow obrigatório da Construtora para qualquer tarefa que crie ou altere interface (HTML, CSS, componentes, telas, layout, estilos, textos de UI) em projects/<slug>/. Carregue antes de escrever código de frontend. Orquestra frontend-design (direção visual) e ui-ux-pro-max (regras de UX/acessibilidade) e o QA visual com prints reais.
---

# Design na Construtora

Frontend não está pronto porque o build passou. Está pronto quando a interface foi
desenhada para o produto, implementada, fotografada, criticada, corrigida e
revalidada — com evidência. O verificador da fábrica confere os artefatos abaixo
e roda o QA visual de novo, por conta própria; se faltar algo, o marco falha.

## Quem faz o quê

| Skill | Responsabilidade | Não usar para |
|---|---|---|
| `frontend-design` | Direção visual e identidade: tipografia, paleta, composição, o "único elemento memorável", copy de interface, autocrítica | Regras de acessibilidade/toque (use a pro-max) |
| `ui-ux-pro-max` | Regras de UX, acessibilidade, toque, formulários, navegação, estados, animação, checklist de entrega — via `search.py --domain ...` | **Definir a identidade.** O `--design-system` dela gera padrões genéricos (testado: sugeriu landing page "storytelling" e fonte manuscrita para um app). Use só como consulta pontual, nunca como direção |
| `factory/scripts/visual_qa.py` | Prints reais (celular e desktop) por fluxo e checks mensuráveis: overflow, contraste, texto pequeno, nome acessível, imagens, erros de console, alvos de toque, sinais de interface genérica | Julgar hierarquia/beleza — isso é a sua inspeção dos prints |
| `factory/design/foundation.css` | Base técnica compartilhada (reset, foco visível, movimento reduzido, safe areas, utilitários) | Identidade — cada produto define seus tokens |

Busca da pro-max (o caminho já resolve no runner):
`python3 "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "<consulta>" --domain ux`
Domínios úteis: `ux`, `typography`, `color`, `icons`, `stack` (`--stack html-tailwind` etc.).

## Workflow (os 8 passos são obrigatórios)

1. **Design brief** → `projects/<slug>/design/brief.md` (modelo: `factory/templates/design-brief.md`).
   Público, contexto de uso (ex.: celular, à noite, 2 minutos), objetivo da tela, tarefas principais em ordem de importância, conteúdo real.
   Em redesign: comece pela **auditoria do que existe**, com prints atuais e a lista de problemas.
2. **Direção visual** (mesma pasta, seção "Direção"): carregue `frontend-design`. Paleta de 4–6 cores nomeadas, tipografia e papéis, conceito de layout com wireframe ASCII, princípios. Revise contra o brief e contra os padrões genéricos listados na skill; escreva o que mudou e por quê.
3. **UX** (seção "UX"): hierarquia, navegação, estados (vazio, carregando, erro, sucesso, offline), feedback de cada ação, responsividade. Consulte a pro-max por domínio para cada decisão não trivial; cite a regra usada.
4. **Implementação**: tokens do produto em `public/tokens.css` (modelo `factory/design/tokens.template.css`), `public/foundation.css` copiado de `factory/design/` sem edição, componentes em CSS próprio. Sem framework/biblioteca nova sem justificativa escrita em `state.decisions`. Não mude lógica de negócio sem necessidade; se mudar, os testes funcionais precisam continuar verdes.
5. **QA visual com prints reais**: declare os fluxos em `projects/<slug>/design/flows.json` cobrindo cada tela e cada estado (use `routes` para simular dados, erro e `hold` para carregando). Rode:
   `python3 factory/scripts/visual_qa.py projects/<slug>/public projects/<slug>/evidence/m<N> --flows projects/<slug>/design/flows.json --commit $(git rev-parse --short HEAD)`
6. **Inspeção e correção**: abra **cada** print com a ferramenta Read e critique como diretor de arte: hierarquia, alinhamento, ritmo de espaçamento, contraste, densidade, consistência, acabamento, o que parece genérico. Zere os bloqueantes; trate ou justifique cada aviso. Corrija.
7. **Revalidação**: rode o passo 5 de novo depois das correções e inspecione os prints novos. Repita até não haver o que corrigir.
8. **Entrega com evidência**: `projects/<slug>/evidence/m<N>/design-review.md` (modelo `factory/templates/design-review.md`) com problemas encontrados, correções, avisos tratados, antes/depois, limitações. No PR, uma seção **QA visual** (prints principais) separada da seção **QA funcional** (testes).

## Regras de qualidade (piso, sem anunciar)

- Responsivo do celular (390px) ao desktop; nada de rolagem horizontal.
- Contraste AA, foco visível, alvos de toque ≥ 44px, `prefers-reduced-motion` respeitado.
- Ícones em SVG com rótulo; nada de emoji como ícone.
- Estados vazio/carregando/erro desenhados, com texto que diz o que fazer.
- Copy em português, frases curtas, verbo de ação nos botões, mesmo nome da ação em todo o fluxo.
- Uma identidade por produto. Não copie a de outro app da fábrica.

## O que o verificador exige (marco com mudança de interface)

- `projects/<slug>/design/brief.md` com seções Brief, Direção e UX.
- `projects/<slug>/design/flows.json`.
- `projects/<slug>/evidence/m<N>/design-review.md` com seções Problemas, Correções e Revalidação.
- O próprio verificador roda `visual_qa.py` no branch do PR: **0 bloqueantes**.
