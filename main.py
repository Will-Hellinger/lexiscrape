import os
import json
import time
import py7zr
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
    cleaned_title = cleaned_title.replace('\n', ' ')
    cleaned_title = cleaned_title.replace('\t', ' ')

    cleaned_title = cleaned_title.replace(', ', ',')
    cleaned_title = cleaned_title.replace(',', ', ')

    cleaned_title: list[str] = cleaned_title.split(', ')
    
    
    for i in range(len(cleaned_title)):
        cleaned_title[i] = cleaned_title[i].strip()

        if cleaned_title[i].endswith('-'):
            cleaned_title[i] = cleaned_title[i][0:-1]
        
        if cleaned_title[i].startswith('-'):
            cleaned_title[i] = cleaned_title[i][1:]
    
    while '-' in cleaned_title:
        cleaned_title.remove('-')
    
    while '' in cleaned_title:
        cleaned_title.remove('')
    
    while ', ' in cleaned_title:
        cleaned_title.remove(', ')
    
    while '_' in cleaned_title:
        cleaned_title.remove('_')

    return cleaned_title


def definition_cleaner(definition: str) -> dict:
    """
    Clean and split the definition string.

    :param definition: The definition string to be cleaned.
    :return list[str]: A list of cleaned definition strings.
    """

    definition = definition.strip()
    definition = definition.lower()

    definition = definition.replace('\n', ' ')
    definition = definition.replace('\t', ' ')

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
    
    for i in range(len(definitions)):
        definitions[i] = definitions[i].strip()

        if definitions[i].endswith('-'):
            definitions[i] = definitions[i][0:-1]
    
    while '-' in definitions:
        definitions.remove('-')
    
    while '' in definitions:
        definitions.remove('')
    
    while ', ' in definitions:
        definitions.remove(', ')
    
    while '_' in definitions:
        definitions.remove('_')
            
    
    definitions = list(set(definitions))

    return definitions


def get_word_info(url: str, session: requests.Session, max_retry_count:int, retry_count: int = 0) -> dict:
    """
    Get the word information from the given URL.

    :param url: The URL of the page to scrape.
    :param session: The requests session to use.
    :param max_retry_count: The maximum number of times to retry a connection before giving up.
    :param retry_count: The current retry count.
    :return dict: A dictionary containing the word information.
    """

    if max_retry_count < retry_count:
        print(f'Maximum retry count reached for {url}. Skipping...')
        
        return {}

    try:
        response = session.get(url)
    except requests.exceptions.ConnectionError:
        print(f'Connection error for {url}. Retrying...')
        return get_word_info(url, session, max_retry_count, retry_count+1)
    
    soup = BeautifulSoup(response.text, 'html.parser')

    flash_card_title = soup.find('div', {'class': 'flash_card_title'})
    flash_card_english_def = soup.find('ol', {'class': 'flash_card_english_def'})
    identification = soup.find('div', {'class': 'main_identification'})

    if not flash_card_title or not flash_card_english_def:
        return {}
    
    orthography_id = None

    if identification:
        orthography_id = int(identification.text.strip().replace('Orthography ID = ', ''))

    cleaned_title = title_cleaner(flash_card_title.text)
    definitions: list = []

    for definition in flash_card_english_def.find_all('li'):
        cleaned_definition = definition_cleaner(definition.text.strip())
        definitions += cleaned_definition

    return {
        'orthography_id': orthography_id,
        'title(s)': cleaned_title,
        'definitions': definitions
    }


def get_paradigm_info(url: str, session: requests.Session, max_retry_count: int, retry_count: int = 0) -> dict:
    """
    Get the paradigm information from the given URL.

    :param url: The URL of the page to scrape.
    :param session: The requests session to use.
    :param max_retry_count: The maximum number of times to retry a connection before giving up.
    :param retry_count: The current retry count.
    :return dict: A dictionary containing the paradigm information.
    """

    if max_retry_count < retry_count:
        print(f'Maximum retry count reached for {url}. Skipping...')

        return {}

    try:
        response = session.get(url)
    except requests.exceptions.ConnectionError:
        print(f'Connection error for {url}. Retrying...')
        return get_paradigm_info(url, session, max_retry_count, retry_count+1)
    
    soup = BeautifulSoup(response.text, 'html.parser')

    paradigm_containers = soup.find_all('div', {'class': 'noun_paradigm_container'})

    if paradigm_containers is None:
        print('No containers')
        return {}

    paradigm_info: dict = {'forms' : len(paradigm_containers)}
    
    for i in range(len(paradigm_containers)):
        current_table = paradigm_containers[i]
        table_dictionary = {}

        if current_table is None:
            print('No table')
            continue

        rows = current_table.find_all('tr')
        columns = []

        for c in range(1, len(rows[0].find_all('td'))):
            columns.append(rows[0].find_all('td')[c].text.strip().lower())
            table_dictionary[columns[c-1]] = {}

        for r in range(1, len(rows)):
            cells = rows[r].find_all('td')
            
            row_header = cells[0].text.strip().lower()

            for c in range(1, len(cells)):
                table_dictionary[columns[c-1]][row_header] = definition_cleaner(cells[c].text.strip().lower())

        paradigm_info[str(i)] = table_dictionary

    return paradigm_info


def get_word_links(url: str, session: requests.Session, max_retry_count: int, retry_count: int = 0) -> list[str]:
    """
    Get the links to the words from the given URL.

    :param url: The URL of the page to scrape.
    :param session: The requests session to use.
    :param max_retry_count: The maximum number of times to retry a connection before giving up.
    :param retry_count: The current retry count.
    :return list: A list of links to the words.
    """

    if max_retry_count < retry_count:
        print(f'Maximum retry count reached for {url}. Skipping...')
        
        return []

    try:
        response: requests.Reponse = session.get(url)
    except requests.exceptions.ConnectionError:
        print(f'Connection error for {url}. Retrying...')
        return get_word_links(url, session, max_retry_count, retry_count+1)

    soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')
    
    a_soup: list = soup.find_all('a')
    word_links: list[str] = []

    for a in a_soup:
        word: str = a.get('href')

        if word is not None and 'definition.php' in word and word not in word_links:
            word_links.append(word)
    
    return word_links


def scrape_thread(word_links: list[str], dictionary_dir: str, paradigm_dir: str, url: str, thread_number: int, ssl_slowdown: bool, max_retry_count: int) -> None:
    """
    Scrape the words from the given list of links.

    :param word_links: The list of links to scrape.
    :param dictionary_dir: The directory to save the dictionary data.
    :param paradigm_dir: The directory to save the paradigm data.
    :param url: The base URL of the website.
    :param thread_number: The number of the thread.
    :param ssl_slowdown: Whether to enable SSL slowdown.
    :param max_retry_count: The maximum number of times to retry a connection before giving up.
    :return None:
    """

    global hashing_key

    start_time = time.time()
    session = requests.Session()

    if thread_number < 10:
        thread_number = f'0{thread_number}'

    print(f'Thread {thread_number} started...')

    for i in range(len(word_links)):
        link = word_links[i]
        word_info = get_word_info(f'{url}{link}', session, max_retry_count)

        if not word_info or word_info == {}:
            continue

        paradigm_info = {}

        orthography_id = word_info.get('orthography_id')

        if orthography_id is not None:
            paradigm_info = get_paradigm_info(f'{url}paradigms.php?p1={orthography_id}', session, max_retry_count)

        if ssl_slowdown:
            time.sleep(0.1)

        if i % 100 == 0 and i != 0:
            eta_time = int((time.time() - start_time) * (len(word_links) - i) / i)
            eta_time = int(eta_time * 100) / 100

            if eta_time < 60:
                print(f'Thread {thread_number} scraped {i}/{len(word_links)} links | ETA: {eta_time} second(s)')
            elif eta_time < 3600:
                print(f'Thread {thread_number} scraped {i}/{len(word_links)} links | ETA: {round(eta_time/60)} minute(s)')
            else:
                print(f'Thread {thread_number} scraped {i}/{len(word_links)} links | ETA: {int(eta_time/3600)} hour(s) & {int((eta_time%3600)/60)} minute(s)')

        for title in word_info.get('title(s)', []):
            title_hash = hashlib.md5(title.encode()).hexdigest()
            dictionary_file_name = f'{dictionary_dir}{os.sep}{title_hash}.json'
            paradigm_file_name = f'{paradigm_dir}{os.sep}{title_hash}.json'

            if title_hash not in hashing_key:
                hashing_key[title_hash] = title


            if not os.path.exists(paradigm_file_name):
                paradigm_info['word'] = title.lower()

                with open(paradigm_file_name, 'w', encoding='unicode-escape') as file:
                    json.dump(paradigm_info, file)


            if not os.path.exists(dictionary_file_name):
                with open(dictionary_file_name, 'w', encoding='unicode-escape') as file:
                    json.dump({"word" : title, "definitions": word_info.get('definitions')}, file)
                
                continue

            with open(dictionary_file_name, 'r+', encoding='unicode-escape') as file:
                try:
                    file_info = json.load(file)
                except json.decoder.JSONDecodeError:
                    print(f'Error reading {dictionary_file_name}. Assuming empty... | title: {repr(title)}')
                    file_info = {}

                definitions = word_info.get('definitions')
                file_definitions = file_info.get('definitions', [])

                for definition in definitions:
                    if definition not in file_definitions:
                        file_definitions.append(definition)

                if definitions != file_definitions:
                    file_info['definitions'] = file_definitions
                    file.seek(0)
                    file.truncate()
                    json.dump(file_info, file)
        
    total_time = int((time.time() - start_time) * 100)/100

    if total_time < 60:
        print(f'Thread {thread_number} took: {int(total_time)} second(s) to scrape')
    elif total_time < 3600:
        print(f'Thread {thread_number} took: {int(total_time/60)} minute(s) to scrape')
    else:
        print(f'Thread {thread_number} took: {int(total_time/3600)} hour(s) & {int((total_time%3600)/60)} minute(s) to scrape')


def main(url: str, latin_dictionaries: dict, latin_dictionary: str, output_dir: str, thread_count: int, package: bool, compression_type: str, ssl_slowdown: bool, cache_links: bool, use_cache: bool, max_retry_count: int) -> None:
    """
    Main function to scrape the Latin Lexicon website.

    :param url: The base URL of the website.
    :param latin_dictionaries: The Latin dictionaries to scrape.
    :param latin_dictionary: The Latin dictionary to scrape.
    :param output_dir: The directory to save the scraped data.
    :param thread_count: The number of threads to use for scraping.
    :param package: Whether to package the dictionary into a zip file.
    :param ssl_slowdown: Whether to enable SSL slowdown.
    :param cache_links: Whether to cache the links to the words.
    :param use_cache: Whether to use the cached links to the words.
    :param max_retry_count: The maximum number of times to retry a connection before giving up.
    :return None:
    """

    global hashing_key
    hashing_key = {}

    dictionary_dir = os.path.join(output_dir, 'dictionary')
    paradigm_dir = os.path.join(output_dir, 'paradigm')

    if not os.path.exists(dictionary_dir):
        os.makedirs(dictionary_dir)
    
    if not os.path.exists(paradigm_dir):
        os.makedirs(paradigm_dir)

    start_time: float = time.time()
    all_word_links: list = []

    total_link_count: int = len(string.ascii_lowercase) * len(latin_dictionaries.get(latin_dictionary, []))
    cache_success: bool = False

    if use_cache:
        with open(f'.{os.sep}all_word_links.json', 'r') as file:
            all_word_links = json.load(file).get(latin_dictionary, [])

            if all_word_links != []:
                cache_success = True
            else:
                print('Cache is empty, scraping links...')
    
    if not cache_success:
        link_count: int = 0
        session: requests.Session = requests.Session()
        
        for letter in string.ascii_lowercase:
            for dictionary in latin_dictionaries.get(latin_dictionary, []):
                current_word_links = get_word_links(f'{url}browse_latin.php?p1={letter}&p2={dictionary}', session, max_retry_count)
                all_word_links += current_word_links
                link_count += 1
                print(f'Found {len(current_word_links)} links | {link_count}/{total_link_count} links scraped   ', end='\r')
    
    if cache_links and not cache_success:
        with open(f'.{os.sep}all_word_links.json', 'w') as file:
            json.dump({latin_dictionary : all_word_links}, file)
    
    if thread_count > total_link_count:
        print('It is not recommended to use more threads than the number of links. (I dont even know why you would do this)')
        print(f'Setting thread count to {total_link_count}...')
        thread_count = total_link_count
    
    all_word_links = list(set(all_word_links))

    print(f'Found {len(all_word_links)} links to scrape...          ')

    link_chunks = [all_word_links[i::thread_count] for i in range(thread_count)]

    threads = []

    for i in range(thread_count):
        thread = threading.Thread(target=scrape_thread, args=(link_chunks[i], dictionary_dir, paradigm_dir, url, i+1, ssl_slowdown, max_retry_count))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    with open(os.path.join(output_dir, 'hashing_key.json'), 'w', encoding='unicode-escape') as file:
        json.dump(hashing_key, file)

    if package:
        print('Packaging dictionary...')

        if os.path.exists(f'{output_dir}.{compression_type}'):
            os.remove(f'{output_dir}.{compression_type}')
            print(f'{output_dir}.{compression_type} already exists, deleting...')
        
        match compression_type: #allows for greater control in future if needed
            case 'zip':
                shutil.make_archive(output_dir, 'zip', output_dir, '.', True)
            
            case '7z':
                with py7zr.SevenZipFile(f'{output_dir}.{compression_type}', 'w') as archive:
                    archive.writeall(output_dir, '/')
            
        print('Creating checksum...')
        checksum = hashlib.md5(open(f'{output_dir}.{compression_type}', 'rb').read()).hexdigest()

        with open(f'.{os.sep}checksum.txt', 'w') as file:
            file.write(checksum)

    total_time = int((time.time() - start_time) * 100)/100

    if total_time < 60:
        print(f'Total time taken: {int(total_time)} second(s)')
    elif total_time < 3600:
        print(f'Total time taken: {int(total_time/60)} minute(s)')
    else:
        print(f'Total time taken: {int(total_time/3600)} hour(s) & {int((total_time%3600)/60)} minute(s)')


if __name__ == "__main__":
    info: dict = json.load(open('info.json', 'r')) 

    latin_dictionaries: dict = info.get('latin_dictionaries')
    url: str = info.get('url')

    parser = argparse.ArgumentParser(description='Build a dictionary from Latin Lexicon website.')

    parser.add_argument('--url', default=url, help='Base URL of the website')
    parser.add_argument('--output-dir', default=f'.{os.sep}data{os.sep}', help='Directory to build the dictionary in')
    parser.add_argument('--thread-count', type=int, default=2, help='Number of threads to use for scraping')
    parser.add_argument('--package', action='store_true', help='Package the dictionary into a zip file')
    parser.add_argument('--compression-type', choices=['zip', '7z'], default='7z', help='Type of compression to use (only for package option)')
    parser.add_argument('--ssl-slowdown', action='store_true', help='Enable SSL slowdown (in case pf timeouts)')
    parser.add_argument('--latin-dictionary', choices=latin_dictionaries.keys(), default="ALL", help='Select a Latin dictionary to build')
    parser.add_argument('--cache-links', action='store_true', help='Cache the links to the words')
    parser.add_argument('--use-cache', action='store_true', help='Use the cached links to the words (if available)')
    parser.add_argument('--max-retry-count', type=int, default=3, help='Number of times to retry a connection before giving up')

    args = parser.parse_args()

    output_dir: str = os.path.abspath(args.output_dir)
    thread_count: int = args.thread_count

    if thread_count < 1:
        thread_count = 1
        print('Thread count cannot be less than 1. Setting thread count to 1')

    if os.path.exists(output_dir):
        confirm: str = input(f'{output_dir} already exists. Do you want to delete it? (Y/n): ')

        if confirm.lower() == 'y' or confirm == '':
            shutil.rmtree(output_dir)
        else:
            print('Aborting. Please provide a new directory.')
            exit(1)
    
    if (os.path.exists(f'.{os.sep}checksum.txt') or os.path.exists(f'.{os.sep}data.{args.compression_type}')) and args.package:
        confirm: str = input(f'Seems as if there is already a package in this directory. Do you want to delete it? (Y/n): ')

        if confirm.lower() == 'y' or confirm == '':
            if os.path.exists(f'.{os.sep}checksum.txt'):
                os.remove(f'.{os.sep}checksum.txt')
            
            if os.path.exists(f'.{os.sep}data.{args.compression_type}'):
                os.remove(f'.{os.sep}data.{args.compression_type}')

    os.makedirs(output_dir, exist_ok=True)

    main(url, latin_dictionaries, args.latin_dictionary, output_dir, thread_count, args.package, args.compression_type, args.ssl_slowdown, args.cache_links, args.use_cache, args.max_retry_count)