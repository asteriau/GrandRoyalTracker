"""Count Grand Royal Skins seen on the Hypixel auction house."""
import base64
import gzip

ITEM_ID = b"CROWN_OF_AVARICE_ROYAL"
# NBT string tag: type 8, name length 4, "uuid", value length 36
UUID_TAG = b"\x00\x04uuid\x00\x24"


def extract_uuid(item_bytes):
    raw = gzip.decompress(base64.b64decode(item_bytes))
    if ITEM_ID not in raw:
        return None
    i = raw.find(UUID_TAG)
    if i < 0:
        return None
    return raw[i + len(UUID_TAG):i + len(UUID_TAG) + 36].decode("ascii")
