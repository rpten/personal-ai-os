#!/usr/bin/env bash
# Coleta os RSS públicos de Letterboxd/Goodreads para $OUT (lidos pelo app em ./data/).
# Se uma fonte falhar, mantém o arquivo anterior e sai com erro só se nenhuma funcionar.
set -u
OUT="${OUT:-./out}"; mkdir -p "$OUT"
LB_USER="rafaeldez"; GR_ID="196111676"; ok=0
fetch() { # nome url
  local tmp; tmp="$(mktemp)"
  if curl -fsSL --max-time 60 --retry 2 -A "Mozilla/5.0 (taste-memory sync)" "$2" -o "$tmp" && grep -q "<item>" "$tmp"; then
    mv "$tmp" "$OUT/$1.xml"; ok=$((ok+1)); echo "$1: ok ($(grep -c '<item>' "$OUT/$1.xml") itens)"
  else rm -f "$tmp"; echo "$1: falhou (mantendo versão anterior)"; fi
}
fetch letterboxd "https://letterboxd.com/${LB_USER}/rss/"
fetch goodreads "https://www.goodreads.com/review/list_rss/${GR_ID}?shelf=read&per_page=200&sort=date_read"
date -u +%FT%TZ > "$OUT/updated.txt"
[ "$ok" -gt 0 ]
