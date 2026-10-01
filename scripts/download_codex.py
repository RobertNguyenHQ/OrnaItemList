"""Download the Orna codex database using thecodexclient (67au/OrnaCodexCrawler)
and split out the item list, skill (spell) list and status effects.

Environment variables:
  OUTPUT_DIR   output folder (default: data)
  CODEX_LANGS  comma-separated languages (default: en)
  FORCE        "true" to ignore the saved ETag and re-download
"""
import gzip
import json
import os
import sys
from pathlib import Path

from thecodexclient.client import TheCodexClient

OUT = Path(os.environ.get("OUTPUT_DIR", "data"))
LANGS = [l.strip() for l in os.environ.get("CODEX_LANGS", "en").split(",") if l.strip()]
FORCE = os.environ.get("FORCE", "").lower() in ("1", "true", "yes")

# Section names to look for in the database (case-insensitive)
SECTIONS = {
    "items": ("items", "item"),
    "skills": ("spells", "spell", "skills", "skill", "abilities"),
    "status_effects": ("status_effects", "statuses", "status", "effects",
                       "status_effect", "conditions", "buffs", "debuffs"),
}

# Keys inside items/skills/monsters that usually hold status effects
EFFECT_KEYS = ("cause", "causes", "give", "gives", "immunit",
               "status", "effect", "buff", "debuff")

SUMMARY = []


# ---------------------------------------------------------------- helpers

def log(msg):
    print(msg)
    SUMMARY.append(msg)


def write_json(path, data, pretty=True):
    with open(path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def describe(data):
    """Short description of the top-level structure, for the run summary."""
    def kind(v):
        if isinstance(v, list):
            return f"list[{len(v)}]"
        if isinstance(v, dict):
            return f"dict[{len(v)}]"
        return type(v).__name__
    if isinstance(data, dict):
        return ", ".join(f"`{k}`: {kind(v)}" for k, v in data.items())
    return kind(data)


def find_section(data, names):
    """Look for a section by key name at the top level or one level deeper."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() in names:
                return k, v
        for parent, v in data.items():
            if isinstance(v, dict):
                for k, vv in v.items():
                    if k.lower() in names:
                        return f"{parent}.{k}", vv
    # Fallback: a flat list of entries that each carry a category/type field
    if isinstance(data, list) and data and isinstance(data[0], dict):
        for field in ("category", "type", "codex_type"):
            if field in data[0]:
                hits = [e for e in data if str(e.get(field, "")).lower() in names]
                if hits:
                    return f"[{field}]", hits
    return None, None


def collect_effects(data):
    """Walk the whole database and collect every status effect referenced
    under keys like causes/gives/immunities. Returns {name_or_id: info}."""
    found = {}

    def entry_for(key):
        return found.setdefault(str(key), {"seen_in": set()})

    def add(value, source_key):
        if isinstance(value, (str, int)):
            entry_for(value)["seen_in"].add(source_key)
        elif isinstance(value, dict):
            key = value.get("id") or value.get("name") or value.get("slug")
            if key is None:
                return
            entry = entry_for(key)
            entry["seen_in"].add(source_key)
            for k in ("id", "name", "icon", "description", "chance"):
                if k in value:
                    entry[k] = value[k]

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                is_effect_key = any(w in k.lower() for w in EFFECT_KEYS)
                if is_effect_key and isinstance(v, list):
                    # e.g. "causes": ["Poison", ...] or [{"name": "Poison", "chance": 50}]
                    for x in v:
                        add(x, k)
                elif (is_effect_key and isinstance(v, dict) and v
                      and all(isinstance(x, (int, float)) for x in v.values())):
                    # e.g. "causes": {"Poison": 50, "Burning": 20}
                    for name in v:
                        entry_for(name)["seen_in"].add(k)
                else:
                    walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)

    walk(data)
    for v in found.values():
        v["seen_in"] = sorted(v["seen_in"])
    return dict(sorted(found.items()))


def parse_body(body):
    """Return (json_data or None, raw_bytes). Handles gzip-compressed bodies."""
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    try:
        return json.loads(body), body
    except ValueError:
        return None, body


# ---------------------------------------------------------------- main logic

def download(client, lang):
    d = OUT / lang
    d.mkdir(parents=True, exist_ok=True)
    etag_file = d / "etag.txt"
    etag = None
    if not FORCE and etag_file.exists():
        etag = etag_file.read_text().strip() or None

    r = client.api.database(lang=lang, etag=etag)
    if r.status_code == 304:
        log(f"**[{lang}]** not modified since last run (ETag match), skipped.")
        return True
    if r.status_code != 200:
        log(f"**[{lang}]** HTTP {r.status_code}: {r.text[:300]}")
        return False

    data, body = parse_body(r.content)

    if data is None:
        # Not JSON: save the raw file so it can be inspected
        if body[:2] == b"PK":
            ext = ".zip"
        elif body[:15] == b"SQLite format 3":
            ext = ".sqlite"
        else:
            ext = ".bin"
        (d / f"database{ext}").write_bytes(body)
        log(f"**[{lang}]** response is not JSON "
            f"({r.headers.get('content-type')}); saved as database{ext}")
    else:
        write_json(d / "database.json", data, pretty=False)
        log(f"**[{lang}]** database.json saved. Top-level structure: {describe(data)}")

        # 1) Items, skills and (if present) a dedicated status-effect section
        for label, names in SECTIONS.items():
            key, section = find_section(data, names)
            if section is None:
                log(f"**[{lang}]** WARNING: no {label} section found, check database.json")
                continue
            write_json(d / f"{label}.json", section)
            size = len(section) if hasattr(section, "__len__") else "?"
            log(f"**[{lang}]** {label}.json saved from `{key}` ({size} entries)")

        # 2) Status effects referenced inside items/skills/monsters
        effects = collect_effects(data)
        if effects:
            write_json(d / "status_effects_referenced.json", effects)
            log(f"**[{lang}]** status_effects_referenced.json: {len(effects)} "
                f"unique effects found in items/skills/monsters")
        else:
            log(f"**[{lang}]** no status-effect references found, check database.json")

    if r.headers.get("ETag"):
        etag_file.write_text(r.headers["ETag"])
    return True


def main():
    ok = True
    with TheCodexClient() as client:
        for lang in LANGS:
            try:
                ok &= download(client, lang)
            except Exception as e:  # keep going with other languages
                log(f"**[{lang}]** ERROR: {e!r}")
                ok = False

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("## Orna codex download\n\n" + "\n\n".join(SUMMARY) + "\n")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
