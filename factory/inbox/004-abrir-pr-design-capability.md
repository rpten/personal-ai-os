Pedido de Rafael (07/11): abra o PR da melhoria da fábrica que já está no branch `fabrica/design-capability-v1`. Não altere o branch.

Comando: `gh pr create --base main --head fabrica/design-capability-v1 --title "Fábrica: Design Capability v1" --body-file <arquivo com o corpo abaixo>`

Corpo do PR (copie exatamente):

---
Torna design uma capacidade obrigatória da Construtora. Detalhes em `docs/design.md`.

**Skills (auditadas, vendorizadas sem modificação, procedência e hashes em `factory/design/vendor.json`)**
- `frontend-design` (Anthropic, Apache-2.0): direção visual e identidade de cada produto.
- `ui-ux-pro-max` (MIT, 100% offline, só Python padrão): regras de UX, acessibilidade, toque e estados. O gerador de "design system" dela não decide identidade (produziu direção genérica no teste).
- `fabrica-design` (nossa): workflow de 8 passos (brief → direção → UX → implementação → QA visual → inspeção e correção → revalidação → entrega).

**Acionamento automático:** descrição da skill + protocolo (`CLAUDE.md` §3) + portão no verificador, que exige brief/direção/UX, fluxos e revisão, e **roda o QA visual de novo no branch do PR** (0 bloqueantes). Não retroage sobre marcos anteriores.

**QA visual (`factory/scripts/visual_qa.py`):** prints reais por fluxo, no celular e no desktop, e checks automáticos (rolagem horizontal, elementos fora da tela, contraste, texto pequeno, nome acessível, imagens, erros de console, alvos de toque, sinais de interface genérica). QA funcional e QA visual agora são seções separadas no PR.

**Testes:** 62 testes (13 novos). Os checks de teste deste branch rodam a cada push.

**Ao mergear:** a fábrica começa sozinha o redesign do Taste Memory (M7) com a nova capacidade (`factory/inbox/005-taste-memory-redesign.md`).

👉 **Sua vez:** mergear para ativar a capacidade e iniciar o piloto.
---

Depois comente o link do PR na issue #3 em uma linha, terminando com 👉 **Sua vez:** mergear o PR para ativar a capacidade e iniciar o redesign.
