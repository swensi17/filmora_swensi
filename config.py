import os

# Список зеркал в порядке приоритета
MIRRORS = [
    'https://hdrezka.ag',
    'https://flymaterez.net'
]

# Функция для получения рабочего зеркала
def get_working_mirror():
    import requests
    from requests.exceptions import RequestException
    
    for mirror in MIRRORS:
        try:
            response = requests.get(mirror, timeout=5)
            if response.status_code == 200:
                return mirror
        except RequestException:
            continue
    return MIRRORS[0]  # Возвращаем первое зеркало, если ни одно не доступно

# Базовые настройки
BASE_URL = get_working_mirror()
CACHE_TIMEOUT = 300  # 5 минут
MAX_REQUESTS_PER_MINUTE = 60

# Настройки безопасности
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
CSRF_ENABLED = True

# Настройки кэширования
CACHE_TYPE = "simple"
