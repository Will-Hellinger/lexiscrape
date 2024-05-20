import os
import json
import time
import string
import hashlib
import argparse
import requests
from bs4 import BeautifulSoup


def title_cleaner(title: str) -> list[str]:
    cleaned_title: str = ' '.join(title.split())

    cleaned_title: list[str] = cleaned_title.split(', ')

    while '-' in cleaned_title:
        cleaned_title.remove('-')

    return cleaned_title


def definition_cleaner(definition: str) -> dict:
    if '[' in definition and ']' in definition:
        start: int = definition.index('[')
        end: int = definition.index(']') + 2

        if end >= len(definition):
            definition = definition[0:start]
        else:
            definition = definition[end:]
    
    if '(' in definition:
        start: int = definition.index('(')
        end: int = len(definition)

        if ')' in definition:
            end = definition.index(')') + 2

        if end >= len(definition):
            definition = definition[0:start]
        else:
            definition = definition[end:]


    definitions: list[str] = definition.split(', ')

    while '-' in definitions:
        definitions.remove('-')
    
    while '' in definitions:
        definitions.remove('')

    while ', ' in definitions:
        definitions.remove(', ')

    return definitions


def get_word_info(url: str) -> dict:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    flash_card_title = soup.find('div', {'class': 'flash_card_title'})
    flash_card_english_def = soup.find('ol', {'class': 'flash_card_english_def'})

    cleaned_title = title_cleaner(flash_card_title.text)
    definitions: list = []

    definition_list = flash_card_english_def.find_all('li')
    for definition in definition_list:
        cleaned_definition = ' '.join(definition.text.split())
        cleaned_definition = definition_cleaner(cleaned_definition)
        definitions += cleaned_definition

    word_info: dict = {
        'title(s)': cleaned_title,
        'definitions' : definitions
    }

    return word_info


def get_word_links(url: str) -> list:
    response: requests.Reponse = requests.get(url)
    soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')
    
    a_soup: list = soup.find_all('a')
    word_links: list = []

    for a in a_soup:
        word: str = a.get('href')

        if word is not None and 'definition.php' in word and word not in word_links:
            word_links.append(word)
    
    return word_links


def main(output_dir: str) -> None:
    url: str = 'https://latinlexicon.org/'

    total_time: float = 0

    if output_dir[-1] != os.sep:
        output_dir += os.sep
    
    dictionary_key: dict = {}

    for letter in string.ascii_lowercase:
        start_time: float = time.time()

        word_links: list = get_word_links(f'{url}browse_latin.php?p1={letter}')
        word_links_length = len(word_links)

        print(f'{letter} has {len(word_links)} words, starting to scrape...')
        
        for i in range(word_links_length):
            if i % 100 == 0:
                print(f'{i}/{word_links_length} words scraped', end='\r')

            word_info: dict = get_word_info(f'{url}{word_links[i]}')

            for title in word_info.get('title(s)'):
                title_hash: str = hashlib.md5(title.encode()).hexdigest()
                file_name = f'{output_dir}{title_hash}.json'

                if title_hash not in dictionary_key:
                    dictionary_key[title] = title_hash
                
                if os.path.exists(file_name):
                    with open(file_name, 'r') as file:
                        file_info = json.load(file)
                    
                    if word_info.get('definitions') != file_info.get('definitions'):
                        with open(file_name, 'w') as file:
                            json.dump({"definitions": word_info.get('definitions') + file_info.get('definitions')}, file)
                else:
                    with open(file_name, 'w') as file:
                        json.dump({"definitions": word_info.get('definitions')}, file)

        stop_time: float = time.time()
        total_time += stop_time - start_time
        print(f'{letter} took {stop_time - start_time} seconds to scrape')
    
        with open(f'{output_dir}dictionary_key.json', 'w') as file:
            json.dump(dictionary_key, file)
    
    print(f'Total time to scrape: {total_time} seconds')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Build a dictionary from Latin Lexicon website.')
    parser.add_argument('--output-dir', default=f'.{os.sep}data{os.sep}', help='Directory to build the dictionary in')
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    if os.path.exists(output_dir):
        print(f'{output_dir} already exists, please provide a new directory')
        exit(1)
    os.makedirs(output_dir, exist_ok=True)

    main(output_dir)