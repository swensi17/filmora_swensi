// Список зеркал в порядке приоритета
const MIRRORS = [
    'https://hdrezka.ag',
    'https://flymaterez.net'
];

// Функция для получения рабочего зеркала
async function getWorkingMirror() {
    for (const mirror of MIRRORS) {
        try {
            const response = await fetch(mirror, { method: 'HEAD', timeout: 5000 });
            if (response.ok) {
                return mirror;
            }
        } catch (error) {
            console.log(`Mirror ${mirror} is not available`);
        }
    }
    return MIRRORS[0]; // Возвращаем первое зеркало, если ни одно не доступно
}

// API клиент
class ApiClient {
    constructor() {
        this.baseUrl = null;
        this.initialized = false;
    }

    async initialize() {
        if (!this.initialized) {
            this.baseUrl = await getWorkingMirror();
            this.initialized = true;
        }
    }

    async searchMovies(query) {
        await this.initialize();
        try {
            const response = await fetch(`${this.baseUrl}/search?do=search&subaction=search&q=${encodeURIComponent(query)}`);
            return await response.json();
        } catch (error) {
            console.error('Search error:', error);
            return [];
        }
    }

    async getPopularMovies() {
        await this.initialize();
        try {
            const response = await fetch(`${this.baseUrl}/popular/`);
            return await response.json();
        } catch (error) {
            console.error('Popular movies error:', error);
            return [];
        }
    }

    async getNewMovies() {
        await this.initialize();
        try {
            const response = await fetch(`${this.baseUrl}/new/`);
            return await response.json();
        } catch (error) {
            console.error('New movies error:', error);
            return [];
        }
    }

    async getNowWatching() {
        await this.initialize();
        try {
            const response = await fetch(`${this.baseUrl}/watching/`);
            return await response.json();
        } catch (error) {
            console.error('Now watching error:', error);
            return [];
        }
    }

    async getMovieDetails(url) {
        await this.initialize();
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('Movie details error:', error);
            return null;
        }
    }
}

// Создаем и экспортируем экземпляр API клиента
const api = new ApiClient();
