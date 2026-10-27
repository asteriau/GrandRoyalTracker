"""Count Grand Royal Skins seen on the Hypixel auction house."""
import base64
import gzip
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ITEM_ID = b"CROWN_OF_AVARICE_ROYAL"
# NBT string tag: type 8, name length 4, "uuid", value length 36
UUID_TAG = b"\x00\x04uuid\x00\x24"

WINDOW_DAYS = 30


def extract_uuid(item_bytes):
    raw = gzip.decompress(base64.b64decode(item_bytes))
    if ITEM_ID not in raw:
        return None
    i = raw.find(UUID_TAG)
    if i < 0:
        return None
    return raw[i + len(UUID_TAG):i + len(UUID_TAG) + 36].decode("ascii")


def parse(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def aggregate_days(sales):
    by_day = {}
    for end, price, _item in sales.values():
        by_day.setdefault(end[:10], []).append(price)
    return {
        day: {"sold": len(p), "coins": sum(p), "median": int(statistics.median(p)), "low": min(p), "high": max(p)}
        for day, p in by_day.items()
    }


def merge(state, sales, listed, active, now):
    skins = {k: list(v) for k, v in state["skins"].items()}
    kept = dict(state["sales"])
    cutoff = fmt(parse(now[:10] + "T00:00:00Z") - timedelta(days=WINDOW_DAYS))

    def seen(item, when):
        first, count = skins.get(item, [when, 0])
        skins[item] = [min(first, when), count]

    for s in sales:
        seen(s["item"], s["end"])
        if s["auction"] not in kept:
            kept[s["auction"]] = [s["end"], s["price"], s["item"]]
            skins[s["item"]][1] += 1
    for l in listed:
        seen(l["item"], l["start"])

    kept = {a: v for a, v in kept.items() if v[0] >= cutoff}
    days = dict(state["days"])
    days.update(aggregate_days(kept))
    return {
        "updated": now,
        "skins": skins,
        "sales": kept,
        "days": days,
        "active": active if active is not None else state["active"],
    }


def check_no_shrink(old, new):
    missing = set(old["skins"]) - set(new["skins"])
    assert not missing, f"skin set would shrink by {len(missing)}"


UA = "GrandRoyalTracker (github.com/asteriau/GrandRoyalTracker)"
COFL = "https://sky.coflnet.com/api/auctions/tag/CROWN_OF_AVARICE_ROYAL/sold?page={}"
HYPIXEL = "https://api.hypixel.net/v2/skyblock/auctions?page={}"
EMPTY = {"updated": "", "skins": {}, "sales": {}, "days": {}, "active": None}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def coflnet_sales():
    out, page = [], 0
    while True:
        rows = get(COFL.format(page))
        if not rows:
            return out
        for r in rows:
            item = (r.get("flattenedNbt") or {}).get("uuid")
            if item:
                out.append({"auction": r["uuid"], "end": r["end"][:19] + "Z", "price": r["highestBidAmount"], "item": item})
        page += 1


def hypixel_active():
    first = get(HYPIXEL.format(0))
    pages = [first] + [get(HYPIXEL.format(p)) for p in range(1, first["totalPages"])]
    listed, bins = [], []
    for page in pages:
        for a in page["auctions"]:
            if a["item_name"] != "Grand Royal Skin":
                continue
            item = extract_uuid(a["item_bytes"])
            if not item:
                continue
            listed.append({"item": item, "start": fmt(datetime.fromtimestamp(a["start"] / 1000, timezone.utc))})
            if a["bin"]:
                bins.append(a["starting_bid"])
    now = fmt(datetime.now(timezone.utc))
    return listed, {"at": now, "count": len(listed), "lowest_bin": min(bins) if bins else None}


def main(path, now=None, fetch_sales=coflnet_sales, fetch_active=hypixel_active):
    now = now or fmt(datetime.now(timezone.utc).replace(microsecond=0))
    try:
        old = json.load(open(path))
    except FileNotFoundError:
        old = EMPTY
    sales, listed, active = [], [], None
    ok = 0
    try:
        sales = fetch_sales()
        ok += 1
    except Exception as e:
        print("coflnet failed:", e, file=sys.stderr)
    try:
        listed, active = fetch_active()
        ok += 1
    except Exception as e:
        print("hypixel failed:", e, file=sys.stderr)
    if not ok:
        return 1
    new = merge(old, sales, listed, active, now)
    check_no_shrink(old, new)
    if {k: v for k, v in new.items() if k != "updated"} == {k: v for k, v in old.items() if k != "updated"}:
        return 0
    with open(path, "w") as f:
        json.dump(new, f, separators=(",", ":"))
    print(f"{len(new['skins'])} skins, {len(new['sales'])} sales in window")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
