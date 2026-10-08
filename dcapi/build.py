import json
import logging
import os.path
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from .models import Character


def join(values):
    """Field berisi banyak nilai (list di JSON) disimpan sebagai satu teks."""
    return '; '.join(values) if values else None


def build_characters(db):
    log.log(logging.INFO, "build_characters")
    with open(os.path.join(os.path.dirname(__file__), 'data/json/characters.json'),
              'r', encoding='utf-8') as datafile:
        characters_dict = json.loads(datafile.read())

    Character.all().delete()
    for index, char in enumerate(characters_dict):
        appearance = char['first_appearance']
        parameters = dict(
            id=index,
            age=char['age'],
            aliases=join(char['aliases']),
            date_of_birth=join(char['date_of_birth']),
            drama_actor=join(char['drama_actor']),

            manga_first_appearance=appearance['manga'],
            anime_first_appearance=appearance['anime'],
            other_first_appearance=appearance['other'],

            # Dulu: 'Female' if gender == 'F' else 'Male' -> semua perempuan jadi 'Male'
            gender=char['gender'],
            keyhole=char['keyhole'],

            english_anime_name=char['name']['english']['anime'],
            english_manga_name=char['name']['english']['manga'],
            kanji_name=char['name']['japanese']['kanji'],
            romanized_name=char['name']['japanese']['romanized'],

            occupation=join(char['occupation']),
            japanese_voice=join(char['voice']['japanese']),
            english_voice=join(char['voice']['english']),
        )
        row = Character.create(**parameters)
        log.log(logging.INFO, str(row) + " : " + parameters['romanized_name'])

    db.commit()


def build_all(db):
    log.log(logging.INFO, "build_all")
    build_characters(db)
