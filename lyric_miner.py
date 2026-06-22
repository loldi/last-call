#!/usr/bin/env python3
"""
lyric_miner.py - find songs that say when the party stops (or never does).

Scans a lyrics CSV (columns: song, year, artist, genre, lyrics) for a curated
set of duration/stop phrases, detects city mentions, geocodes them via the
offline geonamescache gazetteer, scores each song, and writes a ranked
candidate CSV.

Copyright note: the output stores the *category that matched* (e.g. "break_of_dawn"),
never the raw lyric text. Lyrics are read only to classify, never reproduced.

Usage:
    python3 lyric_miner.py --csv lyrics.csv --out candidates.csv --top 40
"""
import argparse, csv, re, sys
from collections import defaultdict
from geonamescache import GeonamesCache

# ---------------------------------------------------------------- phrase rules
# label: (regex, category, weight). category in {"stops","forever"}.
PATTERNS = {
    # --- parties that STOP at a stated time/condition (strong signals) ---
    "break_of_dawn": (r"break of dawn", "stops", 3),
    "til_sunrise":   (r"\b(?:til|till|until)\b[^.\n]{0,22}\b(?:sunrise|sun comes? up|sun is up|daybreak)\b", "stops", 3),
    "til_morning":   (r"\b(?:til|till|until)\b[^.\n]{0,14}\bmornin", "stops", 3),
    "clock_time":    (r"\b(?:til|till|until)\b[^.\n]{0,14}\b(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b[^.\n]{0,10}\b(?:o'?clock|a\.?m\.?|in the mornin)", "stops", 4),
    "early_am":      (r"\b(?:[2-6]|two|three|four|five|six)\s+(?:in the\s+)?mornin", "stops", 2),
    "closing_time":  (r"\bclosing time\b", "stops", 3),
    "last_call":     (r"\blast call\b", "stops", 2),
    "cops_shut":     (r"\b(?:police|cops|po-?po)\b[^.\n]{0,22}\bshut", "stops", 2),
    # --- parties that NEVER stop ---
    "party_dont_stop": (r"\bparty\b[^.\n]{0,14}\b(?:don'?t|do not|won'?t|never)\s+stop", "forever", 3),
    "dont_stop_party": (r"\b(?:don'?t|never)\s+stop[^.\n]{0,14}\bparty", "forever", 3),
    "never_sleeps":    (r"\bnever sleeps\b", "forever", 3),
    "all_night_long":  (r"\ball night long\b", "forever", 2),
    "party_all_night": (r"\bparty\b[^.\n]{0,10}\ball night\b", "forever", 3),
    "never_stop":      (r"\bnever stop(?:s|ping)?\b", "forever", 2),
    "party_hard":      (r"\bparty hard\b", "forever", 2),
    "til_we_drop":     (r"\b(?:til|till|until) (?:we|i|you) drop\b", "forever", 2),
    "all_night":       (r"\ball night\b", "forever", 1),  # broad, low weight
}
COMPILED = {k: (re.compile(p, re.I), cat, w) for k, (p, cat, w) in PATTERNS.items()}

# ---------------------------------------------------------------- city gazetteer
# canonical -> surface forms to match in lyrics (word-boundary, case-insensitive)
CITY_FORMS = {
    "Atlanta": ["atlanta", "atl"], "Miami": ["miami"],
    "New York": ["new york", "new york city", "nyc", "manhattan"],
    "Brooklyn": ["brooklyn"], "Bronx": ["the bronx", "bronx"], "Harlem": ["harlem"],
    "Los Angeles": ["los angeles", "l\\.a\\."], "Hollywood": ["hollywood"],
    "Compton": ["compton"], "Watts": ["watts"], "Long Beach": ["long beach"],
    "Oakland": ["oakland"], "San Francisco": ["san francisco", "frisco"],
    "Las Vegas": ["las vegas", "vegas", "sin city"],
    "Chicago": ["chicago", "chi-town", "chi town"], "Detroit": ["detroit", "motor city", "motown"],
    "Houston": ["houston", "h-town"], "Dallas": ["dallas"], "Austin": ["austin"],
    "New Orleans": ["new orleans", "nola"], "Memphis": ["memphis"], "Nashville": ["nashville"],
    "Philadelphia": ["philadelphia", "philly"], "Boston": ["boston"], "Seattle": ["seattle"],
    "Baltimore": ["baltimore", "b-more"], "Washington": ["washington dc", "d\\.c\\."],
    "Cleveland": ["cleveland"], "Minneapolis": ["minneapolis"], "St. Louis": ["st\\. louis", "st louis"],
    "Kansas City": ["kansas city"], "Denver": ["denver"], "Portland": ["portland"],
    "Phoenix": ["phoenix"], "San Diego": ["san diego"], "Newark": ["newark"],
    # international
    "London": ["london"], "Paris": ["paris"], "Tokyo": ["tokyo"], "Berlin": ["berlin"],
    "Amsterdam": ["amsterdam"], "Ibiza": ["ibiza"], "Kingston": ["kingston"],
    "Havana": ["havana"], "Rio de Janeiro": ["rio de janeiro", "rio"], "Bangkok": ["bangkok"],
    "Toronto": ["toronto"], "Dublin": ["dublin"], "Seoul": ["seoul"],
}
# coords for places the gazetteer treats as neighborhoods/boroughs, not cities
COORD_OVERRIDE = {
    "New York": (40.7128, -74.0060),
    "Brooklyn": (40.6782, -73.9442), "Bronx": (40.8448, -73.8648),
    "Harlem": (40.8116, -73.9465), "Hollywood": (34.0928, -118.3287),
    "Watts": (33.9403, -118.2423), "Long Beach": (33.7701, -118.1937),
}

def build_city_index():
    """Resolve coords (lat,lng) for each canonical city from the gazetteer."""
    gc = GeonamesCache()
    by_name = defaultdict(list)
    for c in gc.get_cities().values():
        by_name[c["name"].lower()].append(c)
    coords, missing = {}, []
    for canon in CITY_FORMS:
        if canon in COORD_OVERRIDE:
            coords[canon] = COORD_OVERRIDE[canon]; continue
        hits = by_name.get(canon.lower(), [])
        if not hits:
            missing.append(canon); continue
        best = max(hits, key=lambda c: c.get("population", 0))  # famous = most populous
        coords[canon] = (round(best["latitude"], 4), round(best["longitude"], 4))
    if missing:
        print(f"[warn] no gazetteer coords for: {', '.join(missing)}", file=sys.stderr)
    # one compiled regex per canonical (alternation of its surface forms)
    matchers = {canon: re.compile(r"\b(?:" + "|".join(forms) + r")\b", re.I)
                for canon, forms in CITY_FORMS.items()}
    return coords, matchers

def deslug(s):
    return re.sub(r"\s+", " ", s.replace("-", " ")).strip().title()

def norm_title(s):
    """Collapse covers/remixes/variants to a shared key (e.g. 'Song (Remix)' -> 'song')."""
    s = s.lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)
    s = re.sub(r"\bfeat.*$", " ", s)
    s = re.sub(r"\b(remix|remaster|remastered|live|acoustic|version|edit|explicit|clean|bonus|demo|instrumental|reprise|radio|extended|original|mix)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s

def scan(csv_path, coords, matchers):
    csv.field_size_limit(10_000_000)
    rows, n = [], 0
    with open(csv_path, newline="", encoding="utf-8", errors="ignore") as fh:
        for r in csv.DictReader(fh):
            n += 1
            lyr = (r.get("lyrics") or "").lower()
            if len(lyr) < 40:
                continue
            phrase_hits, cats, score = [], set(), 0
            for label, (rx, cat, w) in COMPILED.items():
                if rx.search(lyr):
                    phrase_hits.append(label); cats.add((label, cat)); score += w
            if not phrase_hits:
                continue
            city_hits = [c for c, mx in matchers.items() if mx.search(lyr)]
            if not city_hits:
                continue  # for a MAP we only keep songs that name a place
            # pick the city whose canonical coords we have, prefer first match order
            city = next((c for c in city_hits if c in coords), city_hits[0])
            lat, lng = coords.get(city, ("", ""))
            stops = sum(1 for l, c in cats if c == "stops")
            forever = sum(1 for l, c in cats if c == "forever")
            verdict = "stops" if stops > forever else "forever"
            rows.append({
                "artist": deslug(r.get("artist", "")),
                "song": deslug(r.get("song", "")),
                "year": r.get("year", ""),
                "genre": r.get("genre", ""),
                "verdict": verdict,
                "city": city, "lat": lat, "lng": lng,
                "labels": "|".join(sorted(phrase_hits)),  # categories, NOT lyric text
                "score": score + 2 + (1 if any(l == "clock_time" for l in phrase_hits) else 0),
            })
    return rows, n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="candidates.csv")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--keep-covers", action="store_true",
                    help="keep every artist's version instead of collapsing by title")
    a = ap.parse_args()

    coords, matchers = build_city_index()
    rows, scanned = scan(a.csv, coords, matchers)
    # 1) exact (artist, song) dedup, keep best score
    best = {}
    for r in rows:
        k = (r["artist"].lower(), r["song"].lower())
        if k not in best or r["score"] > best[k]["score"]:
            best[k] = r
    items = list(best.values())
    # 2) collapse covers / remix variants sharing a normalized title
    if not a.keep_covers:
        groups = {}
        for r in items:
            groups.setdefault(norm_title(r["song"]), []).append(r)
        items = []
        for g in groups.values():
            top = max(g, key=lambda r: int(r["score"]))
            top["versions"] = len(g)
            items.append(top)
    else:
        for r in items:
            r["versions"] = 1
    ranked = sorted(items, key=lambda r: r["score"], reverse=True)

    cols = ["score", "verdict", "city", "lat", "lng", "artist", "song", "year", "genre", "versions", "labels"]
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for r in ranked:
            w.writerow({c: r[c] for c in cols})

    print(f"scanned {scanned:,} songs -> {len(ranked):,} candidates (phrase + city)\n")
    print(f"{'sc':>2} {'verdict':7} {'city':13} {'artist':22} {'song':28} labels")
    print("-" * 110)
    for r in ranked[:a.top]:
        print(f"{r['score']:>2} {r['verdict']:7} {r['city'][:13]:13} {r['artist'][:22]:22} "
              f"{r['song'][:28]:28} {r['labels']}")

if __name__ == "__main__":
    main()
