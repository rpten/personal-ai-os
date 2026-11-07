# Revisão de design — M7

QA automático: `visual-qa.md` (0 bloqueantes, 1 aviso, base `bf0df7d` + ajustes finais).

## Problemas
Primeira rodada: 0 bloqueantes, 34 avisos. Inspeção dos prints (`05-indicacoes-prontas-mobile.png`, `06-chat-aberto-mobile.png`, `10-gosto-mobile.png`, `07-erro-do-worker-mobile.png`):
1. "Não curto" quebrava em duas linhas na grade de 3 botões.
2. Sem espaço entre o texto de apoio e o botão "Me indique 5".
3. Painéis do "Gosto" colados, sem ritmo.
4. Mensagem de erro toda em vermelho (difícil de ler).
5. "Sinopse" sem indício de que abre.
6. Seletor Filmes/Livros com alvo de 40px; fonte Inter sinalizada como padrão.

## Correções
1. Grade 2×2 (Quero em destaque, Já vi, Não curto, Conversar). 2–3. Espaçamentos da escala. 4. Só o título do erro em vermelho. 5. "Ver/Ocultar" no resumo. 6. Alvo de 44px; fonte trocada para Instrument Sans.

## Avisos do QA automático
- `alvo-pequeno` e `tipografia-padrao`: corrigidos.
- `sobreposicao` (barra inferior × botão "Exportar", só no print de página inteira): justificado — a barra é fixa e o print estica a página; o corpo tem folga inferior de 84px, então nada fica coberto de verdade.

## Revalidação
Rodado de novo após as correções: 0 bloqueantes; prints dos 11 fluxos inspecionados em celular. QA funcional (`qa_m7.py`) verde em desktop e celular. Ainda incomoda: capas são tipográficas, não pôsteres reais (decisão: sem imagem externa/chave).

## Antes e depois
Antes: `antes-3-indicacoes-mobile.png` (página única de 3.300px). Depois: `05-indicacoes-prontas-mobile.png`, `06-chat-aberto-mobile.png`, `08-backlog-mobile.png`, `10-gosto-mobile.png`.

## Limitações
Worker simulado nos prints/QA (lógica e Worker não foram alterados; testes existentes verdes). Fontes vêm do Google Fonts (com fallback Georgia/system-ui). Não testado em iOS Safari real nem leitor de tela.
