# Revisão de design — M8

QA automático: `visual-qa.md` (0 bloqueantes, 0 avisos).

## Problemas
Cartão do M7 (`antes-cartao-mobile.png`): sinopse escondida em "Sinopse · Ver", obrigando um toque extra e ficando no fim, depois dos chips.

## Correções
Sinopse sempre visível logo após o título, com rótulo no mesmo estilo dos demais blocos. Tipografia de leitura: 16px, entrelinha 1,6, cor suave (o "Por que você gostaria" segue mais forte), largura máx. 62ch. Removidos `<details>`, "Ver/Ocultar" e o CSS associado.

## Revalidação
Rodado `visual_qa.py` nos 11 fluxos: 0 bloqueantes, 0 avisos. Inspecionados `05-indicacoes-prontas-mobile.png` (sinopse curta, 3 cartões) e `depois-cartao-mobile.png` (sinopse longa, ~6 linhas no celular: leitura confortável, sem estourar).

## Antes e depois
`antes-cartao-mobile.png` → `depois-cartao-mobile.png`.

## Limitações
Worker simulado nos prints. Sem teste em iOS Safari real nem leitor de tela. Sinopses muito longas aumentam o cartão (sem corte, por pedido).
