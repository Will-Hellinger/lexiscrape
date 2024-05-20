import json
import time
import string
import hashlib
import requests
from bs4 import BeautifulSoup


def definition_cleaner(definition: str) -> str:
    if '[' in definition and ']' in definition:
        start = definition.index('[')
        end = definition.index(']') + 2

        if end >= len(definition):
            definition = definition[0:start]
        else:
            definition = definition[end:]
    
    if '(' in definition:
        start = definition.index('(')

        end = len(definition)
        if ')' in definition:
            end = definition.index(')') + 2

        if end >= len(definition):
            definition = definition[0:start]
        else:
            definition = definition[end:]

    definitions = definition.split(', ')

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

    cleaned_title = ' '.join(flash_card_title.text.split())
    definitions: list = []

    definition_list = flash_card_english_def.find_all('li')
    for definition in definition_list:
        cleaned_definition = ' '.join(definition.text.split())
        cleaned_definition = definition_cleaner(cleaned_definition)
        definitions += cleaned_definition

    word_info = {
        'title': cleaned_title,
        'definitions' : definitions
    }

    print(cleaned_title, definitions)

    return None


def get_word_links(url: str) -> list:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    a_soup = soup.find_all('a')
    word_links: list = []

    for a in a_soup:
        word = a.get('href')
        if word is not None and 'definition.php' in word:
            word_links.append(word)
    
    return word_links


def main() -> None:
    url: str = 'https://latinlexicon.org/'

    total_time = 0

    for letter in string.ascii_lowercase:
        start_time = time.time()

        word_links: list = get_word_links(f'{url}browse_latin.php?p1={letter}')
        
        for word_link in word_links:
            get_word_info(f'{url}{word_link}')

        stop_time = time.time()
        total_time += stop_time - start_time
        print(f'{letter} took {stop_time - start_time} seconds to scrape')
    
    print(f'Total time to scrape: {total_time} seconds')


if __name__ == "__main__":
    main()