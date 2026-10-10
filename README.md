# Detective Conan API

Hello Detectives! This API lets you search raw data about *Detective Conan*
characters and cases, derived from the [Detective Conan World](http://www.detectiveconanworld.com)
wiki.

This is a fork of [lethargilistic/dcapi](https://github.com/lethargilistic/dcapi),
rewritten on **FastAPI + SQLite** (the original used Weppy, which is no longer
maintained). The data is stored in JSON files that are loaded into a SQLite
database on first run.

## Setup

1. Clone this repository.
```
   git clone https://github.com/GozyuPolar-ui/dcapiREMAKE.git
   cd dcapiREMAKE
```

2. Install the dependencies.
```
   pip install -r requirements.txt
```

3. Run the server. The database is created automatically on the first run.
```
   python run.py
```

4. Open `http://127.0.0.1:8000/docs` for interactive documentation, or call the
   endpoints below directly.

To rebuild the database after changing the JSON files, delete
`dcapi/databases/dcapi.db` and run `python -m dcapi.database`.

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /v0/characters` | List characters. Query: `q` (search names and aliases), `gender` (`Male`, `Female`, `Unknown`), `limit` (1-100, default 20), `offset` |
| `GET /v0/character/{id}` | One character by id. `404` if not found |
| `GET /v0/character/{name}` | One character by exact name (case-insensitive): romanized, kanji, or English anime/manga name. `404` if not found |
| `GET /v0/character/{id}/cases` | Cases a character appears in. Supports `limit` and `offset` |
| `GET /v0/cases` | List cases. Query: `q` (search title), `character_id`, `limit`, `offset` |
| `GET /v0/case/{id}` | One case with its characters and roles. `404` if not found |

List endpoints return `{"total": ..., "limit": ..., "offset": ..., "results": [...]}`.

### Examples

```
GET /v0/character/Ai Haibara
GET /v0/characters?q=sherry
GET /v0/characters?gender=Female&limit=10&offset=10
GET /v0/cases?q=roller
GET /v0/cases?character_id=19
```

Example character response (trimmed):

```json
{
  "id": 28,
  "name": {
    "japanese": {"romanized": "Ai Haibara", "kanji": "灰原 哀"},
    "english": {"anime": "...", "manga": "..."}
  },
  "age": 18,
  "gender": "Female",
  "aliases": ["Shiho Miyano (real name)", "Sherry"],
  "occupation": ["Teitan Elementary School student", "Detective Boys member"],
  "voice": {"japanese": ["Megumi Hayashibara"], "english": ["Brina Palencia"]},
  "first_appearance": {"manga": "...", "anime": null, "other": null},
  "keyhole": 18
}
```

Fields that hold several values (`aliases`, `occupation`, `date_of_birth`,
`drama_actor`, `voice.*`) are always lists or `null`. Missing data is `null`,
never an empty string.

Each case is one anime episode. It includes the title, Japanese title, episode
number, manga file, air date, the crimes in the episode (type, location, victim,
cause of death, suspects, description), and the characters linked to it with a
role (`appearance`, `detective`, or `victim`). The culprit is not available
because the wiki does not list it in a structured field.

## Updating the data

The scrapers live in `dcapi/data/json/` and write the JSON files the API loads.
They need a few extra packages:

```
pip install mwclient beautifulsoup4 requests
cd dcapi/data/json
```

| Command | Result |
|---|---|
| `python characters.py` | Scrape all characters into `characters.json` |
| `python clean.py` | Re-clean an existing `characters.json` in place |
| `python cases.py cases.json 20` | Try the case scraper on the first 20 pages |
| `python cases.py` | Scrape all episodes into `cases.json` |

After scraping, rebuild the database (see Setup). `python -m dcapi.database`
prints any character names in `cases.json` that were not found in
`characters.json`.

## Project layout

```
run.py                     start the server
dcapi/main.py              FastAPI app and endpoints
dcapi/database.py          builds the SQLite database from the JSON files
dcapi/data/json/           characters.json, cases.json and their scrapers
```

## TODO

* Remove the bundled official character images and use placeholders.
* Fill in missing character data (`age`, `date_of_birth`, `keyhole`).
* Culprit data for cases.
* Cases from manga-only and movie sources.
* Migrate from SQLite to PostgreSQL if it ever makes sense.
* Python wrapper for this API.

## Credits

* Original project by [lethargilistic](https://github.com/lethargilistic/dcapi).
* Data derived from [Detective Conan World](http://www.detectiveconanworld.com).
  Check the wiki's license terms before redistributing the data.
* *Detective Conan* is created by Gosho Aoyama. This is an unofficial fan project.