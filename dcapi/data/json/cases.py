"""Scraper kasus (per episode anime) dari Detective Conan World.

    python cases.py [output.json] [batas_episode]

Contoh:
    python cases.py cases.json 20     # tes 20 halaman pertama
    python cases.py                   # semua -> cases.json

Satu episode = satu entri. Karakter dihubungkan dari field `cast`
(role: appearance) dan `solved-by` (role: detective). Detail kejahatan
(korban, lokasi, penyebab kematian, deskripsi) ada di `crimes`.
Pelaku (culprit) TIDAK tersedia sebagai field terstruktur di wiki, jadi
tidak diambil.
"""
import json
import re
import sys
import time

import characters as chars
import clean

TEMPLATE_RE = re.compile(r'\{\{[^{}]*\}\}')
PAREN_RE = re.compile(r'\([^)]*\)')
SKIP_NAMES = {'', 'n/a', 'none', 'unknown', 'unsolved', '-'}


def plain(value):
    """Teks wiki -> list string bersih (dipisah <br>), atau None."""
    if value is None:
        return None
    value = chars.filter_infobox_entry(value)
    while TEMPLATE_RE.search(value):  # buang template sisa, mis. {{Inline icons|..}}
        value = TEMPLATE_RE.sub('', value)
    return clean.split_multi(value)


def plain_text(value):
    parts = plain(value)
    return ' '.join(parts) if parts else None


def names_from(value, split_and=False):
    """Daftar nama bersih dari satu field infobox."""
    out = []
    for item in plain(value) or []:
        pieces = re.split(r',|&|\band\b', item) if split_and else [item]
        for piece in pieces:
            piece = PAREN_RE.sub('', piece).strip()
            if piece.lower() not in SKIP_NAMES and piece not in out:
                out.append(piece)
    return out


def parse_infobox(text, name):
    """Ambil semua infobox `{{InfoBox <name> ... }}` sebagai list dict."""
    boxes = []
    pattern = r'\{\{InfoBox ' + re.escape(name) + r'(.*?)\n\}\}'
    for match in re.finditer(pattern, text, re.DOTALL | re.MULTILINE | re.IGNORECASE):
        fields = {}
        for line in match.group(1).split('\n|'):
            if line and '=' in line:
                key, value = line.split('=', 1)
                fields[key.strip().lower()] = value.strip()
        boxes.append(fields)
    return boxes


def first_int(value):
    m = re.search(r'\d+', value or '')
    return int(m.group()) if m else None


def parse_episode(text):
    """Teks wiki satu halaman episode -> dict kasus, atau None bila bukan episode."""
    tv = parse_infobox(text, 'TV')
    if not tv:
        return None
    tv = tv[0]

    title = plain_text(tv.get('title'))
    if not title:
        return None

    japanese = plain(tv.get('japanese-title')) or []
    airdate = plain(tv.get('airdate')) or []
    manga = plain_text(tv.get('manga'))
    if manga and manga.lower() in SKIP_NAMES:
        manga = None

    roles = {}  # nama -> role; solved-by menimpa appearance
    for n in names_from(tv.get('cast')):
        roles[n] = 'appearance'
    for n in names_from(tv.get('solved-by'), split_and=True):
        roles[n] = 'detective'

    crimes = []
    for box in parse_infobox(text, 'Crime'):
        crimes.append({
            'type': plain_text(box.get('crime')),
            'location': plain_text(box.get('location')),
            'victim': plain_text(box.get('victim')),
            'cause_of_death': plain_text(box.get('cause-death')),
            'suspects': plain_text(box.get('suspects')),
            'description': plain_text(box.get('description')),
        })
    descriptions = [c['description'] for c in crimes if c['description']]

    return {
        'title': title,
        'japanese_title': japanese[0] if japanese else None,
        'anime_episode': first_int(tv.get('episode')) or first_int(tv.get('int-episode')),
        'manga_file': manga,
        'airdate': airdate[0] if airdate else None,
        'summary': ' '.join(descriptions) or None,
        'crimes': crimes,
        'characters': [{'name': n, 'role': r} for n, r in roles.items()],
    }


def scrape(limit=None, delay=0.1):
    import mwclient

    site = mwclient.Site(('http', 'www.detectiveconanworld.com'), path='/wiki/')
    cases, seen = [], 0
    for page in site.categories['Episodes']:
        if page.namespace != 0:
            continue
        seen += 1
        if limit and seen > limit:
            break
        try:
            case = parse_episode(page.text())
        except Exception as exc:
            print('Gagal:', page.name, repr(exc))
            continue
        if case is None:
            print('Dilewati (bukan episode / tanpa infobox):', page.name)
        else:
            cases.append(case)
        if seen % 50 == 0:
            print('...', seen, 'halaman')
        time.sleep(delay)

    cases.sort(key=lambda c: (c['anime_episode'] is None, c['anime_episode'] or 0))
    return cases


if __name__ == '__main__':
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'cases.json'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    data = scrape(limit)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('Selesai: %d kasus -> %s' % (len(data), out_path))