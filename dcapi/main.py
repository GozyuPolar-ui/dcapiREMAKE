import json
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query

from . import database


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not database.DB_PATH.exists():
        database.build()
    yield


app = FastAPI(
    title="Detective Conan API",
    description="Data karakter Detective Conan (sumber: Detective Conan World).",
    version="0.1.0",
    lifespan=lifespan,
)


def to_dict(row):
    character = json.loads(row["data"])
    character["id"] = row["id"]
    return character


@app.get("/")
def root():
    return {"message": "真実はいつもひとつ！", "docs": "/docs"}


@app.get("/v0/characters")
def list_characters(
    q: Optional[str] = Query(None, description="Cari di semua nama dan alias"),
    gender: Optional[Literal["Male", "Female", "Unknown"]] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    where, params = [], []
    if q:
        where.append("search_text LIKE ?")
        params.append(f"%{q.strip().lower()}%")
    if gender:
        where.append("gender = ?")
        params.append(gender)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    with database.connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM characters {clause}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM characters {clause} ORDER BY id LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [to_dict(r) for r in rows],
    }


@app.get("/v0/character/{character_id:int}")
def get_character_by_id(character_id: int):
    with database.connect() as conn:
        row = conn.execute(
            "SELECT * FROM characters WHERE id = ?", (character_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, f"Karakter dengan id {character_id} tidak ditemukan")
    return to_dict(row)


@app.get("/v0/character/{name}")
def get_character_by_name(name: str):
    """Cocokkan persis (tanpa peduli huruf besar/kecil) ke nama romaji,
    kanji, atau nama Inggris anime/manga."""
    with database.connect() as conn:
        row = conn.execute(
            """SELECT * FROM characters
               WHERE lower(romanized_name) = lower(:n)
                  OR kanji_name = :n
                  OR lower(english_anime_name) = lower(:n)
                  OR lower(english_manga_name) = lower(:n)
               ORDER BY id LIMIT 1""",
            {"n": name.strip()},
        ).fetchone()
    if row is None:
        raise HTTPException(404, f"Karakter '{name}' tidak ditemukan")
    return to_dict(row)