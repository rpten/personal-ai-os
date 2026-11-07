Pedido de Rafael (07/11): abra o PR do branch `fabrica/design-capability-v1.1` para `main`, sem alterar o branch.

Título: `Fábrica: Design Capability v1.1 (QA visual estável)`

Corpo (copie exatamente):

---
Correções vindas da inspeção independente do piloto (Taste Memory, PR #12):

- **QA visual espera animações terminarem antes do print.** Um print do piloto saiu com um cartão invisível (capturado no meio da animação de entrada), o que gera falso problema ou esconde um real.
- **Nova regra bloqueante:** conteúdo coberto por barra fixa sem folga no fim da página. A sobreposição deixa de acusar elementos fixos, porque a rolagem resolve.
- **O agente sempre roda com o `main` mais recente.** No piloto, a execução que fez o redesign começou segundos antes do merge do #11 e rodou com o protocolo anterior. O resultado passou no portão de design numa execução seguinte, mas a ordem não pode depender de sorte.

66 testes verdes; o redesign do #12 passa com 0 bloqueantes e 0 avisos na versão nova.

Pode mergear antes ou depois do #12; os dois não dependem um do outro.
---

Depois comente o link do PR na issue #3 em uma linha.
