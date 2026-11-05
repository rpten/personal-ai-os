// Cloudflare Worker: busca os RSS públicos de Letterboxd/Goodreads e devolve ao app (com CORS).
// Rotas: /letterboxd?user=<usuario>  e  /goodreads?id=<id numérico>
const ALLOWED_ORIGINS = ["https://rpten.github.io"]; // ajuste se o Pages for outro; "*" libera tudo

export function buildTarget(url) {
  const u = new URL(url);
  if (u.pathname === "/letterboxd") {
    const user = u.searchParams.get("user") || "";
    if (!/^[A-Za-z0-9_]{1,40}$/.test(user)) return null;
    return `https://letterboxd.com/${user}/rss/`;
  }
  if (u.pathname === "/goodreads") {
    const id = u.searchParams.get("id") || "";
    if (!/^\d{1,15}$/.test(id)) return null;
    return `https://www.goodreads.com/review/list_rss/${id}?shelf=read&per_page=200&sort=date_read`;
  }
  return null;
}

function cors(origin) {
  const ok = ALLOWED_ORIGINS.includes("*") || ALLOWED_ORIGINS.includes(origin) || /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin || "");
  return { "Access-Control-Allow-Origin": ok ? origin || "*" : ALLOWED_ORIGINS[0], "Vary": "Origin" };
}

export default {
  async fetch(request) {
    const headers = cors(request.headers.get("Origin"));
    if (request.method === "OPTIONS") return new Response(null, { headers });
    const target = buildTarget(request.url);
    if (!target) return new Response("rota ou parâmetro inválido", { status: 400, headers });
    try {
      const r = await fetch(target, { headers: { "User-Agent": "taste-memory/1.0" }, cf: { cacheTtl: 300 } });
      if (!r.ok) return new Response(`origem respondeu ${r.status}`, { status: 502, headers });
      return new Response(await r.text(), { headers: { ...headers, "Content-Type": "application/xml; charset=utf-8" } });
    } catch (e) {
      return new Response("falha ao buscar a origem", { status: 502, headers });
    }
  },
};
