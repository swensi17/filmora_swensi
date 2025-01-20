import os

# Базовые настройки
BASE_URL = 'https://hdrezka.ag'
CACHE_TIMEOUT = 300  # 5 минут
MAX_REQUESTS_PER_MINUTE = 60

# Настройки безопасности
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
CSRF_ENABLED = True

# Настройки кэширования
CACHE_TYPE = "simple"
