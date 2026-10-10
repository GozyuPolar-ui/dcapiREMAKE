import json
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query

from . import database

from pathlib import Path

from fastapi.responses import FileResponse

STATIC = Path(__file__).parent / "static"

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


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(STATIC / "index.html")


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


def case_with_characters(conn, row):
    links = conn.execute(
        """SELECT c.id, c.romanized_name, cc.role
           FROM case_characters cc JOIN characters c ON c.id = cc.character_id
           WHERE cc.case_id = ? ORDER BY cc.role, c.id""",
        (row["id"],),
    ).fetchall()
    extras = json.loads(row["data"]) if row["data"] else {}
    return {
        "id": row["id"],
        "title": row["title"],
        "anime_episode": row["anime_episode"],
        "manga_file": row["manga_file"],
        "summary": row["summary"],
        **extras,
        "characters": [
            {"id": l["id"], "name": l["romanized_name"], "role": l["role"]}
            for l in links
        ],
    }


@app.get("/v0/cases")
def list_cases(
    q: Optional[str] = Query(None, description="Cari judul kasus"),
    character_id: Optional[int] = Query(None, description="Hanya kasus karakter ini"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    where, params = [], []
    if q:
        where.append("search_text LIKE ?")
        params.append(f"%{q.strip().lower()}%")
    if character_id is not None:
        where.append(
            "id IN (SELECT case_id FROM case_characters WHERE character_id = ?)"
        )
        params.append(character_id)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    with database.connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM cases {clause}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM cases {clause} ORDER BY id LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        results = [case_with_characters(conn, r) for r in rows]

    return {"total": total, "limit": limit, "offset": offset, "results": results}


@app.get("/v0/case/{case_id}")
def get_case(case_id: int):
    with database.connect() as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            raise HTTPException(404, f"Kasus dengan id {case_id} tidak ditemukan")
        return case_with_characters(conn, row)


@app.get("/v0/character/{character_id:int}/cases")
def get_character_cases(
    character_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with database.connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM characters WHERE id = ?", (character_id,)
        ).fetchone()
    if exists is None:
        raise HTTPException(404, f"Karakter dengan id {character_id} tidak ditemukan")
    return list_cases(q=None, character_id=character_id, limit=limit, offset=offset)


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