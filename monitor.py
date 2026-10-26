#!/usr/bin/env python3
"""Monitor de ports nativos para PC (decomps/recomps) -> Discord.

1) DESCOBERTA: busca repositórios NOVOS no GitHub (decompilation, recompilation, pc port...).
2) ATUALIZAÇÕES: avisa novas releases dos projetos em watchlist.json + os descobertos.
Estado salvo em state.json (commitado pelo workflow). Primeira execução é silenciosa.
"""
import json, os, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).parent
STATE_FILE = ROOT / "state.json"
WATCHLIST_FILE = ROOT / "watchlist.json"
API = "https://api.github.com"

WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
WEBHOOK_UPDATES = os.environ.get("DISCORD_WEBHOOK_UPDATES") or WEBHOOK
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN") == "1"
MIN_STARS = int(os.environ.get("MIN_STARS", "10"))
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "7"))
REQUIRE_PLATFORM = os.environ.get("REQUIRE_PLATFORM", "1") == "1"

# Plataformas (edite à vontade). Casamento por palavra inteira, sem diferenciar maiúsculas.
PLATFORMS = {
    "Switch": r"switch|nx",
    "PS2": r"ps2|playstation ?2",
    "Xbox": r"xbox(?! ?360)|xbox-original",
    "Xbox 360": r"xbox ?360|x360",
    "N64": r"n64|nintendo 64",
    "GameCube/Wii": r"gamecube|gcn|wii",
    "PS1": r"ps1|psx|playstation ?1",
    "PSP": r"psp",
    "3DS/DS": r"3ds|nds",
    "Dreamcast": r"dreamcast",
}

QUERIES = [
    "decompilation in:name,description,topics",
    "recompilation in:name,description,topics",
    '"pc port" in:name,description,topics',
    '"native port" in:name,description,topics',
]

session = requests.Session()
session.headers.update({"Accept": "application/vnd.github+json", "User-Agent": "ports-monitor"})
if TOKEN:
    session.headers["Authorization"] = f"Bearer {TOKEN}"


def gh(path, params=None):
    for attempt in range(3):
        r = session.get(f"{API}{path}", params=params, timeout=30)
        if r.status_code in (403, 429) and r.headers.get("Retry-After"):
            time.sleep(int(r.headers["Retry-After"]) + 1)
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    return None


def detect_platforms(text):
    found = [n for n, rx in PLATFORMS.items() if re.search(rf"\b(?:{rx})\b", text, re.I)]
    return found


def discord(embed, silent, url=None):
    url = url or WEBHOOK
    if silent or DRY_RUN or not url:
        print("[sem envio]", embed.get("title"))
        return
    while True:
        r = requests.post(url, json={"embeds": [embed]}, timeout=30)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)) + 0.5)
            continue
        r.raise_for_status()
        break
    time.sleep(1)


def requirements_field(repo, game=None):
    text = f"**Jogo necessário:** {game}\n" if game else ""
    text += ("Use o dump do seu próprio jogo original (não distribuímos ROMs/ISOs).\n"
             f"Como extrair e versões aceitas: https://github.com/{repo}#readme")
    return {"name": "📀 ROM/ISO necessária", "value": text[:1024]}


def load_watchlist():
    items = json.loads(WATCHLIST_FILE.read_text()) if WATCHLIST_FILE.exists() else []
    info = {}
    for it in items:
        if isinstance(it, str):
            info[it] = None
        else:
            info[it["repo"]] = it.get("game")
    return info


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()), False
    return {"seen": [], "tracked": [], "releases": {}}, True


def discover(state, silent):
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    for q in QUERIES:
        data = gh("/search/repositories", {
            "q": f"{q} created:>={since} stars:>={MIN_STARS} fork:false archived:false",
            "sort": "stars", "order": "desc", "per_page": 30})
        for repo in (data or {}).get("items", []):
            name = repo["full_name"]
            if name in state["seen"]:
                continue
            blob = " ".join([repo["name"], repo.get("description") or "", " ".join(repo.get("topics", []))])
            plats = detect_platforms(blob)
            if REQUIRE_PLATFORM and not plats:
                continue
            state["seen"].append(name)
            state["tracked"].append(name)
            discord({
                "title": f"🆕 Novo projeto: {name}",
                "url": repo["html_url"],
                "description": (repo.get("description") or "Sem descrição")[:300],
                "color": 0x57F287,
                "fields": [
                    {"name": "Plataformas", "value": ", ".join(plats) or "?", "inline": True},
                    {"name": "⭐ Stars", "value": str(repo["stargazers_count"]), "inline": True},
                    {"name": "Linguagem", "value": repo.get("language") or "?", "inline": True},
                    requirements_field(name),
                ],
                "footer": {"text": "Descoberta automática"},
            }, silent)


def check_releases(state, silent):
    watch = load_watchlist()
    for repo in sorted(set(watch) | set(state["tracked"])):
        rels = gh(f"/repos/{repo}/releases", {"per_page": 1})
        if not rels:
            continue
        rel = rels[0]
        rid = rel["id"]
        old = state["releases"].get(repo)
        state["releases"][repo] = rid
        if old is None or old == rid:   # repo novo na lista: só registra, não avisa
            continue
        body = (rel.get("body") or "").strip()
        discord({
            "title": f"🔄 {repo}: {rel.get('name') or rel['tag_name']}",
            "url": rel["html_url"],
            "description": body[:500] + ("…" if len(body) > 500 else ""),
            "color": 0xFEE75C if rel.get("prerelease") else 0x5865F2,
            "fields": [requirements_field(repo, watch.get(repo))],
            "footer": {"text": "Pré-lançamento" if rel.get("prerelease") else "Nova release"},
        }, silent, WEBHOOK_UPDATES)


def main():
    state, first_run = load_state()
    if first_run:
        print("Primeira execução: registrando estado sem enviar avisos.")
    discover(state, first_run)
    check_releases(state, first_run)
    STATE_FILE.write_text(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
