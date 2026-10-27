"""Count Grand Royal Skins seen on the Hypixel auction house."""
import base64
import gzip
import statistics
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
