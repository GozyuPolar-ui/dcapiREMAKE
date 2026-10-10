import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

BASE = Path(__file__).parent
JSON_PATH = BASE / "data" / "json" / "characters.json"
CASES_PATH = BASE / "data" / "json" / "cases.json"
DB_PATH = BASE / "databases" / "dcapi.db"

SCHEMA = """
CREATE TABLE characters (
    id INTEGER PRIMARY KEY,
    romanized_name TEXT,
    kanji_name TEXT,
    english_anime_name TEXT,
    english_manga_name TEXT,
    gender TEXT,
    search_text TEXT,   -- nama + alias, huruf kecil, untuk pencarian
    data TEXT NOT NULL  -- JSON lengkap satu karakter
);
CREATE INDEX idx_characters_gender ON characters(gender);

CREATE TABLE cases (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    anime_episode INTEGER,
    manga_file TEXT,
    summary TEXT,
    search_text TEXT,
    data TEXT           -- JSON: japanese_title, airdate, crimes
);

CREATE TABLE case_characters (
    case_id INTEGER NOT NULL REFERENCES cases(id),
    character_id INTEGER NOT NULL REFERENCES characters(id),
    role TEXT NOT NULL DEFAULT 'appearance',  -- victim, culprit, suspect, witness, appearance
    PRIMARY KEY (case_id, character_id, role)
);
CREATE INDEX idx_case_characters_character ON case_characters(character_id);
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_name_lookup(characters):
    """nama (huruf kecil) -> id karakter. Nama pertama yang cocok menang."""
    lookup = {}
    for index, c in enumerate(characters):
        name = c["name"]
        names = [
            name["japanese"]["romanized"], name["japanese"]["kanji"],
            name["english"]["anime"], name["english"]["manga"],
        ]
        for n in names:
            if n:
                lookup.setdefault(n.lower(), index)
    # alias paling akhir, supaya nama utama tidak tertimpa alias
    for index, c in enumerate(characters):
        for alias in c["aliases"] or []:
            lookup.setdefault(alias.lower(), index)
    return lookup


CASE_EXTRA_KEYS = ("japanese_title", "airdate", "crimes")


def victim_names(case):
    """Nama korban dari tiap crime (string bisa berisi beberapa nama)."""
    names = []
    for crime in case.get("crimes") or []:
        for piece in re.split(r",|&|\band\b", crime.get("victim") or ""):
            piece = re.sub(r"\([^)]*\)", "", piece).strip()
            if piece:
                names.append(piece)
    return names


def build(db_path=DB_PATH, json_path=JSON_PATH, cases_path=CASES_PATH):
    """Bangun ulang database dari characters.json dan cases.json.

    Mengembalikan (jumlah_karakter, jumlah_kasus, daftar_nama_tak_dikenal).
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    characters = json.loads(json_path.read_text(encoding="utf-8"))
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    for index, c in enumerate(characters):
        name = c["name"]
        parts = [
            name["japanese"]["romanized"], name["japanese"]["kanji"],
            name["english"]["anime"], name["english"]["manga"],
            *(c["aliases"] or []),
        ]
        conn.execute(
            "INSERT INTO characters VALUES (?,?,?,?,?,?,?,?)",
            (
                index,
                name["japanese"]["romanized"],
                name["japanese"]["kanji"],
                name["english"]["anime"],
                name["english"]["manga"],
                c["gender"],
                " | ".join(p for p in parts if p).lower(),
                json.dumps(c, ensure_ascii=False),
            ),
        )

    unknown = []
    cases = []
    if cases_path.exists():
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
    lookup = build_name_lookup(characters)
    for case_id, case in enumerate(cases):
        conn.execute(
            "INSERT INTO cases VALUES (?,?,?,?,?,?,?)",
            (
                case_id,
                case["title"],
                case.get("anime_episode"),
                case.get("manga_file"),
                case.get("summary"),
                " | ".join(
                    p for p in (case["title"], case.get("japanese_title")) if p
                ).lower(),
                json.dumps(
                    {k: case[k] for k in CASE_EXTRA_KEYS if k in case},
                    ensure_ascii=False,
                ),
            ),
        )
        for link in case.get("characters", []):
            character_id = lookup.get(link["name"].lower())
            if character_id is None:
                unknown.append((case["title"], link["name"]))
                continue
            conn.execute(
                "INSERT OR IGNORE INTO case_characters VALUES (?,?,?)",
                (case_id, character_id, link.get("role", "appearance").lower()),
            )

        # Korban yang kebetulan karakter di database ikut ditautkan (diam-diam;
        # sebagian besar korban memang bukan karakter tetap).
        for victim in victim_names(case):
            character_id = lookup.get(victim.lower())
            if character_id is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO case_characters VALUES (?,?,?)",
                    (case_id, character_id, "victim"),
                )

    conn.commit()
    conn.close()
    return len(characters), len(cases), unknown


if __name__ == "__main__":
    n_chars, n_cases, unknown = build()
    print(f"Database dibangun: {n_chars} karakter, {n_cases} kasus -> {DB_PATH}")
    if unknown:
        counts = Counter(name for _, name in unknown)
        print(f"  {len(counts)} nama tidak ditemukan di characters.json "
              f"({len(unknown)} kemunculan), paling sering:")
        for name, n in counts.most_common(15):
            print(f"    {name} ({n}x)")