"""Scraper karakter dari Detective Conan World.

    python characters.py [output.json]     # default: characters.json

Hasil scrape langsung dibersihkan lewat clean.py.
"""
import re
import sys

import clean


def get_character_list():
    import requests
    from bs4 import BeautifulSoup

    r = requests.get('http://www.detectiveconanworld.com/wiki/Category:Characters')
    soup = BeautifulSoup(r.text, 'html.parser')
    # There should only ever be one section
    character_section = soup.find_all('div', id='mw-pages')[0]

    character_list = []
    for character in character_section.find_all('a')[1:]:  # 1 cuts off 'Characters'
        character_list.append(character['href'][6:])  # 6 cuts off /wiki/

    return character_list


def filter_infobox_entry(entry):
    # NB: flags HARUS ditulis `flags=`. Argumen posisi keempat re.sub adalah
    # `count`, bukan `flags` (bug lama: flag tidak pernah berlaku).
    flags = re.DOTALL | re.MULTILINE

    # Remove comments
    entry = re.sub(r'<!--.*?-->', '', entry, flags=flags)

    # Remove references
    entry = re.sub(r'<ref.*?(?:</ref>|/>)', '', entry, flags=flags)

    # Change pipe-links to just visible text
    entry = re.sub(r'\[\[(?:[^\]]*?\|)*([^\]|]*?)\]\]', r'\1', entry, flags=flags)

    # Change language templates to just visible text
    entry = re.sub(r'\{\{lang\|(?:.*?\|)*(.*?)\}\}', r'\1', entry, flags=flags)

    return entry


NOT_CHARACTER_PAGES = {'Akai_family%27s_middle_brother', '%22The_Criminal%22', 'Scar_Akai'}


def get_infobox_json(names):
    import mwclient

    site = mwclient.Site(('http', 'www.detectiveconanworld.com'), path='/wiki/')
    all_characters = []
    for name in names:
        if name in NOT_CHARACTER_PAGES:
            continue

        text = site.pages[name].text()
        match = re.search(r'\{\{InfoBox Char(.*?)\n\}\}', text, re.DOTALL | re.MULTILINE)
        if not match:
            print(name, 'has no infobox?')
            continue

        one_character = dict()
        for line in match.group(1).split('\n|'):
            if line and '=' in line:
                keyword, value = line.split('=', 1)
                one_character[keyword.strip()] = filter_infobox_entry(value.strip())

        all_characters.append(one_character)
    return all_characters


def prepare_json(infoboxes_list):
    """Ubah infobox mentah ke skema akhir (lihat clean.py)."""
    fixed_list = []
    for original in infoboxes_list:
        try:
            romanized = original.get('name')
            english_name = original.get('english-name') or romanized

            keyhole = re.search(r'Volume\s*(\d+)', original.get('keyhole') or '', re.IGNORECASE)

            fixed_dict = {
                'name': {
                    'japanese': {'romanized': romanized,
                                 'kanji': original.get('japanese-name')},
                    'english': {'anime': english_name,
                                'manga': english_name},
                },
                'age': original.get('age'),   # to_int ambil angka pertama
                'gender': original.get('gender'),
                'date_of_birth': original.get('date-of-birth'),
                'occupation': original.get('occupation'),
                'aliases': original.get('aliases'),
                # Field mentah berisi manga + anime sekaligus; dipecah clean.py
                'first_appearance': original.get('first-appearance'),
                'keyhole': int(keyhole.group(1)) if keyhole else None,
                # (dulu ada koma di akhir baris ini sehingga nilainya jadi tuple)
                'voice': {'japanese': original.get('japanese-voice'),
                          'english': original.get('english-voice')},
                'drama_actor': original.get('drama-actor'),
            }
            fixed_list.append(clean.clean_character(fixed_dict))
        except Exception as exc:
            print('Gagal memproses', original.get('name'), repr(exc))
            raise
    return fixed_list


if __name__ == '__main__':
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'characters.json'
    names = get_character_list()
    unprepared = get_infobox_json(names)
    clean.dump(prepare_json(unprepared), out_path)
    print('Selesai:', out_path)
