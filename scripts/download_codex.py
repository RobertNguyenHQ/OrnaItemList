"""Download the Orna codex database using thecodexclient (67au/OrnaCodexCrawler)
and split out the item list and skill (spell) list."""
import gzip
import json
import os
import sys
from pathlib import Path

from thecodexclient.client import TheCodexClient

OUT = Path(os.environ.get("OUTPUT_DIR", "data"))
LANGS = [l.strip() for l in os.environ.get("CODEX_LANGS", "en").split(",") if l.strip()]
FORCE = os.environ.get("FORCE", "").lower() in ("1", "true", "yes")

SECTIONS = {
    "items": ("items", "item"),
    "skills": ("spells", "spell", "skills", "skill", "abilities"),
}
SUMMARY = []


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


def parse_body(body):
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    try:
        return json.loads(body), body
    except ValueError:
        return None, body


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
        ext = ".zip" if body[:2] == b"PK" else ".sqlite" if body[:15] == b"SQLite format 3" else ".bin"
        (d / f"database{ext}").write_bytes(body)
        log(f"**[{lang}]** response is not JSON ({r.headers.get('content-type')}); saved as database{ext}")
    else:
        write_json(d / "database.json", data, pretty=False)
        log(f"**[{lang}]** database.json saved. Top-level structure: {describe(data)}")
        for label, names in SECTIONS.items():
            key, section = find_section(data, names)
            if section is None:
                log(f"**[{lang}]** WARNING: no {label} section found, check database.json")
                continue
            write_json(d / f"{label}.json", section)
            size = len(section) if hasattr(section, "__len__") else "?"
            log(f"**[{lang}]** {label}.json saved from `{key}` ({size} entries)")

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
