import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
JSON_PATH = BASE / "data" / "json" / "characters.json"
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
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build(db_path=DB_PATH):
    """Bangun ulang database dari characters.json."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    characters = json.loads(JSON_PATH.read_text(encoding="utf-8"))
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
    conn.commit()
    conn.close()
    return len(characters)


if __name__ == "__main__":
    print(f"Database dibangun: {build()} karakter -> {DB_PATH}")