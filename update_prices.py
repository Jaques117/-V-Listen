"""Holt FC27-Preise von Futbin und schreibt site/prices.json (laeuft in GitHub Actions)."""
import asyncio, json, os, sys
from datetime import datetime, timezone
from futbin_sdk import FutbinClient, PlayerSearchOptions

PAGES = int(os.environ.get("MAX_PAGES", "40"))   # 40 Seiten = die ~1200 beliebtesten Karten
DIAG = os.environ.get("DIAGNOSE") == "1"

def g(o, *names):
    for n in names:
        v = o.get(n) if isinstance(o, dict) else getattr(o, n, None)
        if v is not None:
            return v
    return None

async def pull(client, platform):
    out, rank = {}, 0
    for page in range(1, PAGES + 1):
        try:
            res = await client.search_players(options=PlayerSearchOptions(
                platform=platform, page=page, sort="popularity", order="desc"))
        except Exception as e:
            print(f"{platform} Seite {page}: {e!r}", file=sys.stderr)
            break
        if not res:
            break
        if DIAG and page == 1:
            print("BEISPIEL:", type(res[0]), res[0])
        for p in res:
            rank += 1
            name = g(p, "name", "player_name", "full_name")
            rating = g(p, "rating", "overall", "ovr")
            price = g(p, "price", f"price_{platform.lower()}", "lowest_bin")
            key = str(g(p, "futbin_id", "id", "player_id") or f"{name}-{rating}")
            if name and rating:
                out[key] = {"n": str(name), "r": int(rating), "p": int(price or 0),
                            "b": int(g(p, "popularity", "pop") or 100000 - rank)}
        await asyncio.sleep(0.6)
    return out

async def main():
    async with FutbinClient() as c:
        ps = await pull(c, "PS")
        pc = await pull(c, "PC")
    cards = []
    for k, v in ps.items():
        cards.append({"n": v["n"], "r": v["r"], "p": [v["p"], pc.get(k, {}).get("p", 0)], "b": v["b"]})
    print(f"{len(cards)} Karten geladen")
    if not cards:
        sys.exit("Keine Daten erhalten - Seite wird nicht aktualisiert")
    with open("site/prices.json", "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(), "cards": cards}, f, ensure_ascii=False)

asyncio.run(main())
