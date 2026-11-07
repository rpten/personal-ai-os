# Memória de gosto — Design (M7, redesign)

## Brief
- **Público e contexto de uso:** Rafael, sozinho, no celular (390px), à noite no sofá, 1–2 minutos: "o que vejo/leio agora?". Desktop é secundário.
- **Objetivo da interface:** pedir indicações em um toque, decidir rápido (quero / já vi / não curto), conversar quando em dúvida, e consultar o backlog.
- **Tarefas, em ordem de importância:** 1. Ver e decidir sobre as 5 indicações. 2. Ler por que cada uma combina (sinopse, referências do histórico). 3. Conversar sobre uma indicação. 4. Navegar entre indicações, backlog, gosto e dados. 5. Layout celular. 6. Tipografia e acabamento. 7. Estados (carregando, erro, vazio).
- **Conteúdo real:** títulos e anos de filmes/livros, autores, notas em estrelas do Letterboxd/Goodreads, sinopse e "por que você gostaria" gerados pelo Gemini, chips com itens do histórico, mensagens do chat.
- **Auditoria do existente** (print: `evidence/m7/antes-3-indicacoes-mobile.png`), do mais grave ao menos grave:
  1. Página única de ~9 telas sem navegação; "Me indique 5" só no 2º bloco, abaixo de estatísticas.
  2. Indicação sem hierarquia: título pequeno, sem capa, sinopse em itálico do mesmo peso que o "por que", rótulo em caixa alta minúscula; 4 botões de mesmo peso.
  3. Abas Filmes/Livros duplicadas (topo e backlog).
  4. Resumo: barras de 8px, listas com marcadores, datas cruas (2019-03-02), "4.25" com ponto.
  5. Funções administrativas (atualizar, CSV, backup) com o mesmo peso do conteúdo; "Choose File" em inglês.
  6. system-ui + azul escuro genérico; emoji como ícone.
  7. Status soltos ("Pronto: 3 indicações em 0s").

## Direção
- **Personalidade:** *Curadoria* (voz de quem conhece você), *íntima* (noite, luz baixa), *editorial* (livro e programa de cinema).
- **Referências do universo:** ingresso/programa de cinema, capa de livro de bolso, ficha de biblioteca.
- **Paleta:** Breu `#15110e` (fundo) · Papel-café `#201a16` (superfície) · Creme `#f4ece0` (texto) · Areia `#b8ab9b` (secundário) · Âmbar de ingresso `#f0a640` (ação, filmes) · Sálvia `#9cc7a8` (livros). Perigo `#ff8f84`, sucesso `#9cc7a8`.
- **Tipografia:** Fraunces (serif de display: títulos, nomes de obras, números) com fallback Georgia; Inter para texto e controles (fallback system-ui). Escala fluida da foundation (`--step-*`).
- **Composição:** barra inferior com 4 destinos; seletor Filmes/Livros único no topo; capas tipográficas (sem imagem externa).
```
┌──────────────────────┐
│ Memória   [Filmes|Livros]│
│ Boa noite. O que     │
│ vemos hoje?  (serif) │
│ [ ✦ Me indique 5 ]   │
│  ▸ direcionar        │
│ ┌──┐ Oldboy          │
│ │O │ 2003            │
│ └──┘ POR QUE…texto   │
│  baseado em: chips   │
│  [Quero][Já vi][Não] │
│  💬 Conversar        │
├──────────────────────┤
│ Indicar Backlog Gosto Dados │
└──────────────────────┘
```
- **O elemento memorável:** a capa tipográfica — bloco colorido por título (matiz derivada do nome) com a inicial gigante em serif e o ano, como uma lombada/cartaz, no lugar da imagem que não temos.
- **Revisão contra o genérico:** o primeiro esboço era "escuro + roxo/azul + cartões iguais". Troquei por paleta quente (âmbar/sálvia), serifa expressiva, cartão de indicação em destaque (maior que os demais elementos) e ação primária única por cartão.

## UX
- **Hierarquia:** *Indicar*: botão principal → cartões (título serif grande > "por que você gostaria" > sinopse recolhida > referências) → ação primária "Quero", secundárias "Já vi/Já li", terciária "Não curto", e "Conversar". *Backlog*: lista + "O que combina agora?". *Gosto*: resumo. *Dados*: administrativo, discreto.
- **Navegação:** barra inferior fixa com 4 destinos (Indicar, Backlog, Gosto, Dados) e seletor Filmes/Livros global (um só). Hash na URL (`#backlog`) permite voltar/compartilhar.
- **Estados:** vazio (primeiro acesso) → cartão com passo a passo e botão "Ir para Dados"; carregando → esqueletos dos cartões + barra de progresso com tempo; erro → caixa `role=alert` com mensagem e "Tentar de novo"; sucesso → toast discreto ("Guardado no backlog"); backlog vazio explica como encher.
- **Feedback:** botões marcados ficam preenchidos (`aria-pressed`); toast de 2,5s (`role=status`); chat mostra "Pensando…" como bolha.
- **Responsividade:** coluna única até 720px; acima, conteúdo centralizado (max 720px) e a barra de navegação vira barra superior/lateral compacta, sem mudar a estrutura.
- **Regras consultadas (ui-ux-pro-max):** consulta a `ux`/`typography` para navegação inferior (≤5 itens, rótulo + ícone), alvos ≥44px, não depender só de cor (marcado = preenchido + ícone ✓), `prefers-reduced-motion`, esqueletos em vez de spinner para carregamento > 1s.

## M8 — Sinopse sempre visível (ajuste)
- **Brief:** Rafael (07/11) quer a sinopse direto no cartão, sem "Ver/Ocultar", para livros e filmes.
- **Direção:** ordem do cartão: título → Sinopse → Por que você gostaria → Do seu histórico → ações. A sinopse descreve o item e vem antes; o "por que" fica em texto claro e mais forte, o que mantém a hierarquia (sinopse em cinza suave, 16px, entrelinha 1,6, máx. 62ch).
- **UX:** nada escondido atrás de clique; sinopse ausente simplesmente não ocupa espaço.
