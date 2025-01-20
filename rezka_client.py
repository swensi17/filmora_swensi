import requests
from bs4 import BeautifulSoup
from hdrezka_api import HdRezkaApi
import re
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://rezka.ag"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class RezkaClient:
    def __init__(self):
        self.base_url = 'https://hdrezka.ag'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_movies(self, category):
        """
        Получает список фильмов по категории
        :param category: Категория фильмов ('now', 'new', 'popular')
        :return: Список фильмов
        """
        try:
            if category == 'popular':
                return get_popular_movies()
            
            # URLs для разных категорий
            category_urls = {
                'now': '/film/',  # Сейчас смотрят (главная страница с фильмами)
                'new': '/film/2024/'  # Новинки (фильмы 2024 года)
            }
            
            if category not in category_urls:
                raise ValueError(f'Неизвестная категория: {category}')
            
            url = self.base_url + category_urls[category]
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            movies_list = []
            
            # Находим все карточки фильмов
            movies = soup.find_all('div', class_='b-content__inline_item')
            
            for movie in movies[:20]:  # Ограничиваем до 20 фильмов
                link = movie.find('a')
                if not link:
                    continue
                    
                movie_url = link.get('href', '')
                # Добавляем базовый URL если его нет
                if movie_url and not movie_url.startswith(('http://', 'https://')):
                    movie_url = self.base_url + movie_url
                
                title = link.get('title', '').strip()
                
                # Получаем постер
                poster = movie.find('img')
                poster_url = poster.get('src', '') if poster else ''
                if poster_url and not poster_url.startswith('http'):
                    poster_url = 'https:' + poster_url
                
                # Получаем качество
                quality = None
                quality_elem = movie.find('div', class_='quality')
                if quality_elem:
                    quality = quality_elem.text.strip()
                
                # Получаем год
                year = None
                year_elem = movie.find('div', class_='b-content__inline_item-link').find('div')
                if year_elem:
                    year_match = re.search(r'\d{4}', year_elem.text)
                    if year_match:
                        year = year_match.group()
                
                # Получаем рейтинг
                rating = None
                rating_elem = movie.find('span', class_='rating')
                if rating_elem:
                    rating = rating_elem.text.strip()
                
                movies_list.append({
                    'url': movie_url,
                    'title': title,
                    'poster': poster_url,
                    'quality': quality,
                    'year': year,
                    'rating': rating
                })
            
            return movies_list
            
        except requests.RequestException as e:
            logger.error(f"Error fetching movies: {str(e)}")
            raise Exception(f"Ошибка при получении фильмов: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise Exception(f"Неожиданная ошибка: {str(e)}")

def search_movies(query):
    search_url = f"{BASE_URL}/search/?do=search&subaction=search&q={query}"
    try:
        response = requests.get(search_url, headers=HEADERS)
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        for item in soup.find_all('div', class_='b-content__inline_item'):
            link = item.find('a')
            image = item.find('img')
            info = item.find('div', class_='b-content__inline_item-link')
            
            if link and image and info:
                title = info.find('a').text.strip()
                year = info.find('div').text.strip()
                rating_elem = item.find('i', class_='b-rating_icon')
                rating = rating_elem.text.strip() if rating_elem else "0.0"
                
                results.append({
                    'title': title,
                    'year': year,
                    'rating': rating,
                    'poster': image['src'] if 'src' in image.attrs else '',
                    'url': link['href'] if 'href' in link.attrs else ''
                })
        
        return results
    except Exception as e:
        logger.error(f"Error searching movies: {e}")
        return []

def get_movie_details(url):
    try:
        # Добавляем базовый URL, если его нет
        if not url.startswith('http'):
            url = f'https://hdrezka.ag{url}'
        
        api = HdRezkaApi(url)
        
        # Получаем базовые данные
        movie_data = {
            'title': api.name,
            'url': url,
            'type': api.type,
            'translations': api.getTranslations()
        }
        
        # Получаем постер и дополнительную информацию через BS4
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Получаем постер
        poster_elem = soup.find('img', {'class': 'b-sidecover__image'})
        if poster_elem and 'src' in poster_elem.attrs:
            movie_data['poster'] = poster_elem['src']
        
        # Если это сериал, получаем информацию о сезонах и эпизодах
        if api.type == 'series':
            seasons_data = api.getSeasons()
            if seasons_data:
                movie_data['seasons'] = sorted(list(seasons_data.keys()))
                movie_data['episodes'] = {
                    str(season): sorted(list(episodes.keys()))
                    for season, episodes in seasons_data.items()
                }
            
        return movie_data
        
    except requests.RequestException as e:
        logger.error(f"Error making request: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting movie details: {e}")
        return None

def get_movie_stream(url, translation_id=None, quality=None, season=None, episode=None):
    try:
        # Добавляем базовый URL, если его нет
        if not url.startswith('http'):
            url = f'https://hdrezka.ag{url}'
        
        api = HdRezkaApi(url)
        
        # Получаем стрим с указанными параметрами
        stream_data = api.getStream(
            translation=translation_id,
            resolution=quality,
            season=season,
            episode=episode
        )
        
        return stream_data
        
    except Exception as e:
        logger.error(f"Error getting movie stream: {e}")
        return None

def get_popular_movies():
    try:
        url = f"{BASE_URL}/films/"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        movies_list = []
        
        # Находим все карточки фильмов
        movies = soup.find_all('div', class_='b-content__inline_item')
        
        for movie in movies[:20]:  # Ограничиваем до 20 фильмов
            link = movie.find('a')
            if not link:
                continue
                
            movie_url = link.get('href', '')
            # Добавляем базовый URL если его нет
            if movie_url and not movie_url.startswith(('http://', 'https://')):
                movie_url = BASE_URL + movie_url
            
            title = link.get('title', '').strip()
            
            # Получаем постер
            poster = movie.find('img')
            poster_url = poster.get('src', '') if poster else ''
            if poster_url and not poster_url.startswith('http'):
                poster_url = 'https:' + poster_url
            
            # Получаем качество
            quality = None
            quality_elem = movie.find('div', class_='quality')
            if quality_elem:
                quality = quality_elem.text.strip()
            
            # Получаем год
            year = None
            year_elem = movie.find('div', class_='b-content__inline_item-link').find('div')
            if year_elem:
                year_match = re.search(r'\d{4}', year_elem.text)
                if year_match:
                    year = year_match.group()
            
            # Получаем рейтинг
            rating = None
            rating_elem = movie.find('span', class_='rating')
            if rating_elem:
                rating = rating_elem.text.strip()
            
            movies_list.append({
                'url': movie_url,
                'title': title,
                'poster': poster_url,
                'quality': quality,
                'year': year,
                'rating': rating
            })
        
        return movies_list
        
    except requests.RequestException as e:
        logger.error(f"Error fetching popular movies: {str(e)}")
        raise Exception(f"Ошибка при получении популярных фильмов: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise Exception(f"Неожиданная ошибка: {str(e)}")

def get_stream_url(url, translation_id=None, season=None, episode=None):
    try:
        api = HdRezkaApi(url)
        
        if api.type == 'movie':
            # Пробуем получить стрим в разных разрешениях, начиная с лучшего
            resolutions = ["1080p Ultra", "1080p", "720p", "480p", "360p"]
            for resolution in resolutions:
                try:
                    stream_url = api.getStream(
                        translation=translation_id or '1',
                        resolution=resolution
                    )
                    if stream_url:
                        return {
                            'url': stream_url,
                            'quality': resolution,
                            'type': 'movie'
                        }
                except ValueError:
                    continue
            
            return None
        else:
            # Для сериалов
            if season is None or episode is None:
                return None
            
            # Пробуем получить стрим в разных разрешениях, начиная с лучшего
            resolutions = ["1080p Ultra", "1080p", "720p", "480p", "360p"]
            for resolution in resolutions:
                try:
                    stream_url = api.getStream(
                        translation=translation_id or '1',
                        season=season,
                        episode=episode,
                        resolution=resolution
                    )
                    if stream_url:
                        return {
                            'url': stream_url,
                            'quality': resolution,
                            'type': 'series',
                            'season': season,
                            'episode': episode
                        }
                except ValueError:
                    continue
            
            return None
    except Exception as e:
        logger.error(f"Error getting stream URL: {e}")
        return None

def get_available_streams(url, translation_id=None, season=None, episode=None):
    """Получает список всех доступных стримов с разным качеством"""
    try:
        api = HdRezkaApi(url)
        streams = {}
        
        # Получаем список переводов
        translations = api.getTranslations()
        if not translations:
            return None
            
        # Если translation_id не указан или его нет в списке, берем первый доступный
        if not translation_id or translation_id not in translations.values():
            translation_id = list(translations.values())[0]
        
        if api.type == 'movie':
            # Для фильмов пробуем получить все доступные качества
            resolutions = ["4K", "2K", "1440p", "1080p Ultra", "1080p", "720p", "480p", "360p"]
            for resolution in resolutions:
                try:
                    stream_url = api.getStream(translation=translation_id, resolution=resolution)
                    if stream_url:
                        streams[resolution] = stream_url
                except ValueError:
                    continue
                    
            if streams:
                return {
                    'streams': streams,
                    'type': 'movie',
                    'translations': translations,
                    'current_translation': translation_id
                }
        else:
            # Для сериалов
            if season is None or episode is None:
                return None
                
            resolutions = ["4K", "2K", "1440p", "1080p Ultra", "1080p", "720p", "480p", "360p"]
            for resolution in resolutions:
                try:
                    stream_url = api.getStream(
                        translation=translation_id,
                        season=season,
                        episode=episode,
                        resolution=resolution
                    )
                    if stream_url:
                        streams[resolution] = stream_url
                except ValueError:
                    continue
                    
            if streams:
                return {
                    'streams': streams,
                    'type': 'series',
                    'translations': translations,
                    'season': season,
                    'episode': episode,
                    'current_translation': translation_id
                }
                
        return None
    except Exception as e:
        logger.error(f"Error getting available streams: {e}")
        return None
