import time
import string
import requests
from bs4 import BeautifulSoup


def get_word_info(url: str) -> dict:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    flash_card_title = soup.find('div', {'class': 'flash_card_title'})

    cleaned_title = ' '.join(flash_card_title.text.split())

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