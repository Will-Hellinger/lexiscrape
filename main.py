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
    """
    Clean and split the title string.
    
    :param title: The title string to be cleaned.
    :return list[str]: A list of cleaned title strings.
    """
    cleaned_title: str = title.strip()

    cleaned_title: list[str] = cleaned_title.split(', ')

    while '-' in cleaned_title:
        cleaned_title.remove('-')

    return cleaned_title


def definition_cleaner(definition: str) -> dict:
    """
    Clean and split the definition string.

    :param definition: The definition string to be cleaned.
    :return list[str]: A list of cleaned definition strings.
    """

    definition = definition.strip()
    definition = definition.lower()

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

    while ', ' in definitions:
        definitions.remove(', ')
    
    while '' in definitions:
        definitions.remove('')
    
    for i in range(len(definitions)):
        definitions[i] = definitions[i].strip()

        if definitions[i].endswith('-'):
            definitions[i] = definitions[i][0:-1]
    
    definitions = list(set(definitions))

    return definitions


def get_word_info(url: str, session: requests.Session) -> dict:
    """
    Get the word information from the given URL.

    :param url: The URL of the page to scrape.
    :param session: The requests session to use.
    :return dict: A dictionary containing the word information.
    """

    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    flash_card_title = soup.find('div', {'class': 'flash_card_title'})
    flash_card_english_def = soup.find('ol', {'class': 'flash_card_english_def'})

    if not flash_card_title or not flash_card_english_def:
        return {}

    cleaned_title = title_cleaner(flash_card_title.text)
    definitions: list = []

    for definition in flash_card_english_def.find_all('li'):
        cleaned_definition = definition_cleaner(definition.text.strip())
        definitions += cleaned_definition

    return {
        'title(s)': cleaned_title,
        'definitions': definitions
    }


def get_word_links(url: str) -> list[str]:
    """
    Get the links to the words from the given URL.

    :param url: The URL of the page to scrape.
    :return list: A list of links to the words.
    """

    response: requests.Reponse = requests.get(url)
    soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')
    
    a_soup: list = soup.find_all('a')
    word_links: list[str] = []

    for a in a_soup:
        word: str = a.get('href')

        if word is not None and 'definition.php' in word and word not in word_links:
            word_links.append(word)
    
    return word_links


def scrape_thread(word_links: list[str], output_dir: str, url: str, thread_number: int, ssl_slowdown: bool) -> None:
    """
    Scrape the words from the given list of links.

    :param word_links: The list of links to scrape.
    :param output_dir: The directory to save the scraped data.
    :param url: The base URL of the website.
    :param thread_number: The number of the thread.
    :return None:
    """
    global dictionary_key

    start_time = time.time()
    session = requests.Session()

    print(f'Thread {thread_number} started...')

    for i in range(len(word_links)):
        link = word_links[i]
        word_info = get_word_info(f'{url}{link}', session)

        if not word_info or word_info == {}:
            continue

        if ssl_slowdown:
            time.sleep(0.1)

        if i % 100 == 0 and i != 0:
            print(f'Thread {thread_number} scraped {i}/{len(word_links)} links')

        for title in word_info.get('title(s)', []):
            title_hash = hashlib.md5(title.encode()).hexdigest()
            file_name = f'{output_dir}{os.sep}{title_hash}.json'

            if title_hash not in dictionary_key:
                dictionary_key[title_hash] = title

            if not os.path.exists(file_name):
                with open(file_name, 'w') as file:
                    json.dump({"definitions": word_info.get('definitions')}, file)
            else:
                with open(file_name, 'r') as file:
                    file_info = json.load(file)

                definitions = word_info.get('definitions')
                file_definitions = file_info.get('definitions', [])

                for definition in file_definitions:
                    if definition not in definitions:
                        definitions.append(definition)

                if definitions != file_definitions:
                    with open(file_name, 'w') as file:
                        json.dump({"definitions": definitions}, file)
    stop_time = time.time()

    print(f'Thread {thread_number} took {stop_time - start_time} seconds to scrape')


def main(url: str, latin_dictionary: list[str], output_dir: str, thread_count: int, package: bool, ssl_slowdown: bool) -> None:
    """
    Main function to scrape the Latin Lexicon website.

    :param url: The base URL of the website.
    :param latin_dictionary: The list of Latin dictionaries to scrape.
    :param output_dir: The directory to save the scraped data.
    :param thread_count: The number of threads to use for scraping.
    :param package: Whether to package the dictionary into a zip file.
    :param ssl_slowdown: Whether to enable SSL slowdown.
    :return None:
    """

    global dictionary_key
    dictionary_key = {}

    dictionary_dir = os.path.join(output_dir, 'dictionary')
    if not os.path.exists(dictionary_dir):
        os.makedirs(dictionary_dir)

    start_time = time.time()
    all_word_links = []

    link_count = 0
    total_link_count = len(string.ascii_lowercase) * len(latin_dictionary)

    for letter in string.ascii_lowercase:
        for dictionary in latin_dictionary:
            all_word_links += get_word_links(f'{url}browse_latin.php?p1={letter}&p2={dictionary}')
            link_count += 1
            print(f'Found {len(all_word_links)} links | {link_count}/{total_link_count} links scraped')
    
    all_word_links = list(set(all_word_links))
    link_chunks = [all_word_links[i::thread_count] for i in range(thread_count)]

    threads = []

    for i in range(thread_count):
        thread = threading.Thread(target=scrape_thread, args=(link_chunks[i], dictionary_dir, url, i, ssl_slowdown))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    with open(os.path.join(output_dir, 'dictionary_key.json'), 'w', encoding='unicode-escape') as file:
        json.dump(dictionary_key, file)

    if package:
        print('Packaging dictionary...')

        if os.path.exists(f'{output_dir}.zip'):
            os.remove(f'{output_dir}.zip')
            print(f'{output_dir}.zip already exists, deleting...')

        shutil.make_archive(output_dir, 'zip', output_dir, '.', True)
        print('Creating checksum...')
        checksum = hashlib.md5(open(f'{output_dir}.zip', 'rb').read()).hexdigest()

        with open(f'.{os.sep}checksum.txt', 'w') as file:
            file.write(checksum)

    stop_time = time.time()
    print(f'Total time taken: {stop_time - start_time} seconds')


if __name__ == "__main__":
    info: dict = json.load(open('info.json', 'r')) 

    latin_dictionaries: dict = info.get('latin_dictionaries')
    url: str = info.get('url')

    parser = argparse.ArgumentParser(description='Build a dictionary from Latin Lexicon website.')
    parser.add_argument('--output-dir', default=f'.{os.sep}data{os.sep}', help='Directory to build the dictionary in')
    parser.add_argument('--thread-count', type=int, default=2, help='Number of threads to use for scraping')
    parser.add_argument('--package', action='store_true', help='Package the dictionary into a zip file')
    parser.add_argument('--ssl-slowdown', action='store_true', help='Enable SSL slowdown (in case pf timeouts)')
    parser.add_argument('--latin-dictionary', choices=latin_dictionaries.keys(), default="ALL", help='Select a Latin dictionary to build')
    args = parser.parse_args()

    output_dir: str = os.path.abspath(args.output_dir)
    thread_count: int = args.thread_count

    if thread_count < 1:
        thread_count = 1
    
    if thread_count > len(string.ascii_lowercase):
        print(f'Thread count cannot exceed {len(string.ascii_lowercase)}, setting thread count to {len(string.ascii_lowercase)}.')
        thread_count = len(string.ascii_lowercase)

    if os.path.exists(output_dir):
        confirm: str = input(f'{output_dir} already exists. Do you want to delete it? (Y/n): ')

        if confirm.lower() == 'y' or confirm == '':
            shutil.rmtree(output_dir)
        else:
            print('Aborting. Please provide a new directory.')
            exit(1)

    os.makedirs(output_dir, exist_ok=True)

    main(url, latin_dictionaries.get(args.latin_dictionary), output_dir, thread_count, args.package, args.ssl_slowdown)