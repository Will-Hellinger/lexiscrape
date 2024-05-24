import os
import json
import time
import shutil
import string
import hashlib
import argparse
import requests
import threading
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


def scrape_thread(start_letter: str, end_letter: str, output_dir: str, url: str, thread_number: int) -> None:
    global dictionary_key

    for letter in string.ascii_lowercase[start_letter:end_letter]:
        start_time = time.time()

        word_links = get_word_links(f'{url}browse_latin.php?p1={letter}')
        word_links_length = len(word_links)

        print(f'{letter} has {word_links_length} words, starting to scrape...')
        
        for i in range(word_links_length):
            word_info = get_word_info(f'{url}{word_links[i]}')

            for title in word_info.get('title(s)'):
                title_hash = hashlib.md5(title.encode()).hexdigest()
                file_name = f'{output_dir}{title_hash}.json'

                if title_hash not in dictionary_key:
                    dictionary_key[title_hash] = title
                
                if os.path.exists(file_name):
                    with open(file_name, 'r') as file:
                        file_info = json.load(file)
                    
                    definitions = word_info.get('definitions')

                    for definition in file_info.get('definitions'):
                        if definition not in definitions:
                            definitions.append(definition)

                    if word_info.get('definitions') != file_info.get('definitions'):
                        with open(file_name, 'w') as file:
                            json.dump({"definitions": definitions}, file)
                else:
                    with open(file_name, 'w') as file:
                        json.dump({"definitions": word_info.get('definitions')}, file)

        stop_time = time.time()
        print(f'{letter} took {stop_time - start_time} seconds to scrape')
    
    print(f'Thread {thread_number} has finished scraping')


def main(output_dir: str, thread_count: int) -> None:
    global dictionary_key

    url: str = 'https://latinlexicon.org/'
    dictionary_key = {}

    if output_dir[-1] != os.sep:
        output_dir += os.sep

    start_time = time.time()

    threads = []
    for i in range(thread_count):
        start_letter = i * (26 // thread_count)
        end_letter = (i + 1) * (26 // thread_count) if i != thread_count - 1 else 26
        thread = threading.Thread(target=scrape_thread, args=(start_letter, end_letter, output_dir, url, i))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
    
    with open(f'{output_dir}dictionary_key.json', 'w', encoding='unicode-escape') as file:
        json.dump(dictionary_key, file)
    
    stop_time = time.time()
    print(f'Total time taken: {stop_time - start_time} seconds')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Build a dictionary from Latin Lexicon website.')
    parser.add_argument('--output-dir', default=f'.{os.sep}data{os.sep}', help='Directory to build the dictionary in')
    parser.add_argument('--thread-count', type=int, default=2, help='Number of threads to use for scraping')
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    thread_count = args.thread_count

    if thread_count < 1:
        thread_count = 1
    
    if thread_count > len(string.ascii_lowercase):
        print(f'Thread count cannot exceed {len(string.ascii_lowercase)}, setting thread count to {len(string.ascii_lowercase)}.')
        thread_count = len(string.ascii_lowercase)

    if os.path.exists(output_dir):
        confirm = input(f'{output_dir} already exists. Do you want to delete it? (y/n): ')

        if confirm.lower() == 'y':
            shutil.rmtree(output_dir)
        else:
            print('Aborting. Please provide a new directory.')
            exit(1)

    os.makedirs(output_dir, exist_ok=True)

    main(output_dir, thread_count)