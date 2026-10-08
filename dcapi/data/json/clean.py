"""Pembersihan data karakter.

Dipakai oleh scraper (characters.py) dan bisa dijalankan langsung untuk
membersihkan characters.json yang sudah ada:

    python clean.py                 # bersihkan characters.json di tempat
    python clean.py in.json out.json

Semua fungsi bersifat idempotent: menjalankannya dua kali hasilnya sama.

Skema hasil (per karakter):
    name.japanese.{romanized, kanji}      str | null
    name.english.{anime, manga}           str | null
    age                                   int | null
    gender                                "Male" | "Female" | "Unknown" | null
    date_of_birth                         list[str] | null
    occupation, aliases, drama_actor      list[str] | null
    voice.{japanese, english}             list[str] | null
    first_appearance.{manga, anime, other} str | null
    keyhole                               int | null
"""
import html
import json
import re
import sys

BR_RE = re.compile(r'<\s*br\s*/?\s*>', re.IGNORECASE)
COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
TAG_RE = re.compile(r'<[^>]+>')
EXT_LINK_RE = re.compile(r'\[https?://\S+\s+([^\]]+)\]')
WS_RE = re.compile(r'[ \t\r\f\v\u00a0]+')


def strip_markup(text):
    """Buang sisa komentar HTML, tag, link eksternal wiki, dan entity."""
    text = COMMENT_RE.sub('', text)
    text = EXT_LINK_RE.sub(r'\1', text)
    text = text.replace("'''", '').replace("''", '')
    return html.unescape(text)


def split_multi(value):
    """Pecah string yang dipisah <br> jadi list bersih. Kosong -> None."""
    if value is None:
        return None
    if isinstance(value, list):
        parts = value
    else:
        parts = BR_RE.split(strip_markup(str(value)))
    out = []
    for part in parts:
        part = TAG_RE.sub('', str(part))
        part = WS_RE.sub(' ', part).strip()
        if part:
            out.append(part)
    return out or None


def clean_text(value):
    """String tunggal tanpa markup. Kosong -> None."""
    parts = split_multi(value)
    return ' '.join(parts) if parts else None


def clean_dob(value):
    parts = split_multi(value)
    if not parts:
        return None
    parts = [p for p in parts if p.lower() != 'unknown']
    return parts or None


def clean_gender(value):
    text = clean_text(value)
    if not text:
        return None
    low = text.lower()
    if low in ('m', 'male'):
        return 'Male'
    if low in ('f', 'female'):
        return 'Female'
    return 'Unknown'


def parse_first_appearance(raw):
    """Pecah first appearance gabungan jadi manga / anime / other.

    Contoh input mentah:
      'Manga: File 433<br> Anime: Episode 345'
      'Magic Kaito Chapter 15<br>Manga: File 299<br />Anime: Episode 219'
      'Episode 279 (anime)'
      'Anime: Movie 5'
      'Conan Special: Volume 26'   -> other (bukan label manga/anime)
    """
    result = {'manga': None, 'anime': None, 'other': None}
    others = []
    for part in split_multi(raw) or []:
        m = re.match(r'^(manga|anime)\s*:\s*(.*)$', part, re.IGNORECASE)
        if m:
            value = m.group(2).strip()
            result[m.group(1).lower()] = value or None
            continue
        m = re.match(r'^(.*?)\s*\((manga|anime)\)$', part, re.IGNORECASE)
        if m and m.group(1):
            result[m.group(2).lower()] = m.group(1).strip()
            continue
        others.append(part)
    if others:
        result['other'] = '; '.join(others)
    return result


def merge_first_appearance(fa):
    """Terima format lama ({manga, anime} berisi string mentah yang sama)
    atau format baru, kembalikan format baru."""
    if not isinstance(fa, dict):
        return parse_first_appearance(fa)
    if 'other' in fa:  # sudah format baru
        return {k: clean_text(fa.get(k)) for k in ('manga', 'anime', 'other')}
    raws = []
    for key in ('manga', 'anime'):
        if fa.get(key) and fa[key] not in raws:
            raws.append(fa[key])
    return parse_first_appearance('<br>'.join(raws)) if raws else \
        {'manga': None, 'anime': None, 'other': None}


def to_int(value):
    if isinstance(value, int):
        return value
    text = clean_text(value)
    if not text:
        return None
    m = re.search(r'\d+', text)
    return int(m.group()) if m else None


def clean_character(c):
    voice = c.get('voice')
    if isinstance(voice, list):  # format lama: tuple akibat koma nyasar
        voice = voice[0] if voice else {}
    voice = voice or {}
    name = c.get('name') or {}
    jp = name.get('japanese') or {}
    en = name.get('english') or {}

    return {
        'name': {
            'japanese': {'romanized': clean_text(jp.get('romanized')),
                         'kanji': clean_text(jp.get('kanji'))},
            'english': {'anime': clean_text(en.get('anime')),
                        'manga': clean_text(en.get('manga'))},
        },
        'age': to_int(c.get('age')),
        'gender': clean_gender(c.get('gender')),
        'date_of_birth': clean_dob(c.get('date_of_birth')),
        'occupation': split_multi(c.get('occupation')),
        'aliases': split_multi(c.get('aliases')),
        'first_appearance': merge_first_appearance(c.get('first_appearance')),
        'keyhole': to_int(c.get('keyhole')) or None,  # 0 = tidak ada
        'voice': {'japanese': split_multi(voice.get('japanese')),
                  'english': split_multi(voice.get('english'))},
        'drama_actor': split_multi(c.get('drama_actor')),
    }


def dump(characters, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(characters, f, indent=4, sort_keys=True, ensure_ascii=False)
        f.write('\n')


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'characters.json'
    dst = sys.argv[2] if len(sys.argv) > 2 else src
    with open(src, encoding='utf-8') as f:
        data = json.load(f)
    dump([clean_character(c) for c in data], dst)
    print('Dibersihkan: %d karakter -> %s' % (len(data), dst))
