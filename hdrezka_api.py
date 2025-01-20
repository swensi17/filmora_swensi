import requests
from bs4 import BeautifulSoup
import base64
from itertools import product
import json
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive'
}

class HdRezkaApi:
    __version__ = 2.1
    
    def __init__(self, url):
        self.url = url
        self.name = None
        self.type = None
        self.translators = None
        self.seriesInfo = None
        self.soup = None
        self.initialize()

    def initialize(self):
        """Инициализация API и получение базовой информации"""
        try:
            response = requests.get(self.url, headers=HEADERS)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.text, 'html.parser')
            
            # Получаем название
            title_elem = self.soup.find('h1', itemprop='name')
            self.name = title_elem.text.strip() if title_elem else None
            
            # Определяем тип контента
            if '/series/' in self.url or self.soup.find('div', id='simple-seasons'):
                self.type = 'series'
            else:
                self.type = 'movie'
            
        except Exception as e:
            logger.error(f"Error initializing API: {str(e)}")
            raise ValueError(f"Ошибка при инициализации API: {str(e)}")

    def getTranslations(self):
        """Получает список доступных переводов"""
        try:
            if self.translators is not None:
                return self.translators

            self.translators = {}
            
            # Ищем список переводов
            translators_list = self.soup.find('ul', class_='b-translator__list')
            if translators_list:
                for translator in translators_list.find_all('li'):
                    tr_id = translator.get('data-translator_id')
                    if tr_id:
                        self.translators[translator.text.strip()] = tr_id
                        
            # Если список переводов пуст, проверяем текущий перевод
            if not self.translators:
                current_translator = self.soup.find('div', class_='b-translator__wrapper')
                if current_translator:
                    self.translators[current_translator.text.strip()] = "1"
                    
            # Если все еще нет переводов, добавляем дефолтный
            if not self.translators:
                self.translators["Оригинал"] = "1"
                
            return self.translators
            
        except Exception as e:
            logger.error(f"Error getting translations: {str(e)}")
            return {"Оригинал": "1"}

    def getStream(self, translation=None, resolution=None, season=None, episode=None):
        """Получает ссылку на видео"""
        try:
            # Находим CDN ссылку
            cdn_links = None
            scripts = self.soup.find_all('script')
            for script in scripts:
                if script.string and 'initCDNSeriesEvents' in script.string:
                    cdn_links = script.string
                    break
                elif script.string and 'initCDNMoviesEvents' in script.string:
                    cdn_links = script.string
                    break

            if not cdn_links:
                raise ValueError("Не удалось найти ссылки на видео")

            # Извлекаем параметры для запроса
            id_match = re.search(r"initCDN\w+Events\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*", cdn_links)
            if not id_match:
                raise ValueError("Не удалось получить параметры видео")

            id_video, id_cdn, id_translator = id_match.groups()

            # Формируем данные для POST запроса
            data = {
                'id': id_video,
                'translator_id': translation or id_translator,
                'action': 'get_episodes' if self.type == 'series' else 'get_movie'
            }

            # Для сериалов добавляем season и episode
            if self.type == 'series':
                if not season or not episode:
                    raise ValueError("Для сериала необходимо указать номер сезона и эпизода")
                data['season'] = season
                data['episode'] = episode

            # Делаем POST запрос
            response = requests.post('https://hdrezka.ag/ajax/get_cdn_series/', data=data, headers=HEADERS)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                raise ValueError(result.get('message', 'Неизвестная ошибка'))

            # Получаем список стримов
            streams = {}
            stream_data = result.get('url', '').split(',')
            for stream in stream_data:
                if '[' in stream and ']' in stream:
                    quality = stream[stream.find('[')+1:stream.find(']')]
                    url = stream[stream.find(']')+1:]
                    streams[quality] = url.strip()

            if not streams:
                raise ValueError("Не удалось получить ссылки на видео")

            # Определяем доступные разрешения
            available_resolutions = sorted(list(streams.keys()), key=lambda x: int(x.replace('p', '')))
            
            # Если указано конкретное разрешение, проверяем его наличие
            if resolution:
                if resolution not in streams:
                    resolution = available_resolutions[-1]  # Берем максимальное доступное
            else:
                resolution = available_resolutions[-1]  # Берем максимальное доступное

            return {
                'stream': streams,
                'available_resolutions': available_resolutions,
                'translation': translation or id_translator,
                'resolution': resolution
            }

        except Exception as e:
            logger.error(f"Error getting stream: {str(e)}")
            raise ValueError(f"Ошибка при получении видео: {str(e)}")

    def getSeasons(self):
        """Получает информацию о сезонах и эпизодах сериала"""
        if self.type != 'series':
            return None

        if self.seriesInfo is not None:
            return self.seriesInfo

        try:
            # Ищем div с информацией о сезонах
            seasons_div = self.soup.find('div', id='simple-seasons')
            if not seasons_div:
                return None

            seasons_data = {}
            
            # Получаем все сезоны
            season_items = seasons_div.find_all('li', class_='b-simple_season__item')
            
            for season in season_items:
                season_id = season.get('data-tab_id')
                if not season_id:
                    continue

                # Получаем номер сезона
                season_num = season.get('data-season_id') or season_id
                
                # Находим список эпизодов для этого сезона
                episodes_div = self.soup.find('ul', id=f'simple-episodes-list-{season_id}')
                if not episodes_div:
                    continue

                # Получаем все эпизоды сезона
                episode_items = episodes_div.find_all('li', class_='b-simple_episode__item')
                episodes = {}
                
                for episode in episode_items:
                    episode_num = episode.get('data-episode_id')
                    if episode_num:
                        episodes[episode_num] = {
                            'id': episode_num,
                            'name': episode.get_text(strip=True)
                        }

                if episodes:
                    seasons_data[season_num] = episodes

            self.seriesInfo = seasons_data
            return seasons_data

        except Exception as e:
            logger.error(f"Error getting seasons info: {str(e)}")
            return None
