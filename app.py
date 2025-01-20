from flask import Flask, jsonify, request, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from functools import wraps
from urllib.parse import urlparse
import logging
from rezka_client import get_popular_movies, get_movie_details, get_movie_stream, search_movies, RezkaClient
from hdrezka_api import HdRezkaApi
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300

# Инициализация расширений
csrf = CSRFProtect(app)
cache = Cache(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["60 per minute"]
)

# Создаем единственный экземпляр клиента
rezka_client = RezkaClient()

def validate_url(url):
    """Проверка валидности URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def handle_error(func):
    """Декоратор для обработки ошибок"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return jsonify({
                'error': str(e),
                'status': 'error',
                'endpoint': request.endpoint
            }), 500
    return wrapper

@app.route('/')
@cache.cached(timeout=300)
def index():
    return render_template('index.html')

@app.route('/popular')
@cache.cached(timeout=300)
@handle_error
def popular():
    movies = get_popular_movies()
    return jsonify(movies)

@app.route('/search')
@limiter.limit("60 per minute")
@handle_error
def search():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Поисковый запрос не может быть пустым'}), 400
    
    movies = search_movies(query)
    return jsonify(movies)

@app.route('/movie/details')
@cache.memoize(timeout=300)
@handle_error
def movie_details():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL не указан'}), 400
    
    if not validate_url(url):
        return jsonify({'error': 'Некорректный URL'}), 400
        
    details = get_movie_details(url)
    if not details:
        return jsonify({'error': 'Не удалось получить информацию о фильме'}), 404
        
    return jsonify(details)

@app.route('/movie/stream')
@limiter.limit("60 per minute")
@handle_error
def movie_stream():
    """Получение потока видео для фильма или сериала"""
    url = request.args.get('url', '').strip()
    translation = request.args.get('translation')
    quality = request.args.get('quality', '720p')
    season = request.args.get('season')
    episode = request.args.get('episode')
    
    if not url:
        return jsonify({'error': 'URL не указан'}), 400
    
    try:
        # Создаем API клиент
        api = HdRezkaApi(url)
        
        # Получаем список переводов
        translations = api.getTranslations()
        if not translations:
            return jsonify({'error': 'Не удалось получить список переводов'}), 404
        
        # Если перевод не указан, берем первый доступный
        if not translation or translation not in translations.values():
            translation = next(iter(translations.values()))

        # Проверяем, является ли контент сериалом
        is_series = api.type == 'series'
        
        # Для сериалов требуются номер сезона и эпизода
        if is_series and (not season or not episode):
            # Получаем информацию о сезонах и эпизодах
            seasons_data = api.getSeasons()
            if not seasons_data:
                return jsonify({'error': 'Не удалось получить информацию о сезонах'}), 404
            
            # Берем первый сезон и первый эпизод
            first_season = sorted(seasons_data.keys())[0]
            first_episode = sorted(seasons_data[first_season].keys())[0]
            season = season or first_season
            episode = episode or first_episode
        
        # Получаем данные стрима
        stream_data = api.getStream(
            translation=translation,
            resolution=quality,
            season=season if is_series else None,
            episode=episode if is_series else None
        )
        
        # Формируем словарь со стримами для каждого качества
        streams = {}
        for res in stream_data['available_resolutions']:
            res_data = api.getStream(
                translation=translation,
                resolution=res,
                season=season if is_series else None,
                episode=episode if is_series else None
            )
            streams[res] = res_data['stream'][res]
            
        response_data = {
            'stream': streams,
            'translations': translations,
            'available_resolutions': stream_data['available_resolutions'],
            'current_translation': stream_data['translation'],
            'current_resolution': stream_data['resolution'],
            'url': url,
            'is_series': is_series
        }
        
        if is_series:
            response_data.update({
                'current_season': season,
                'current_episode': episode
            })
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in movie_stream: {str(e)}")
        return jsonify({'error': str(e)}), 404

@app.route('/now')
@cache.cached(timeout=300)
@handle_error
def now_watching():
    movies = rezka_client.get_movies('now')
    return jsonify(movies)

@app.route('/new')
@cache.cached(timeout=300)
@handle_error
def new_movies():
    movies = rezka_client.get_movies('new')
    return jsonify(movies)

if __name__ == '__main__':
    app.run(debug=False)
