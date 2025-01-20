document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const moviesContainer = document.getElementById('moviesContainer');
    const movieModal = document.getElementById('movieModal');
    const closeModal = movieModal.querySelector('.close-modal');
    const loadingStatus = movieModal.querySelector('.loading-status');
    const playerContainer = movieModal.querySelector('.player-container');
    const translationSelect = document.getElementById('translationSelect');
    const qualitySelect = document.getElementById('qualitySelect');
    const videoPlayer = document.getElementById('videoPlayer');
    
    let player = null;
    let currentStreamData = null;
    let currentCategory = 'now';

    // Поиск фильмов
    searchButton.addEventListener('click', () => {
        const query = searchInput.value.trim();
        if (query) {
            loadMovies('search', query);
        }
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const query = searchInput.value.trim();
            if (query) {
                loadMovies('search', query);
            }
        }
    });

    // Обработчики событий для категорий
    const categoryButtons = document.querySelectorAll('.category-btn');
    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            const category = button.dataset.category;
            if (category !== currentCategory) {
                currentCategory = category;
                
                // Обновляем активную кнопку
                categoryButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                // Загружаем фильмы выбранной категории
                loadMovies(category);
            }
        });
    });

    // Загрузка фильмов по категории
    async function loadMovies(category, query = '') {
        try {
            // Показываем индикатор загрузки
            moviesContainer.innerHTML = `
                <div class="loading-indicator">
                    <div class="spinner"></div>
                    <p>${category === 'search' ? `Ищем фильмы по запросу "${query}"...` : 'Загрузка фильмов...'}</p>
                </div>
            `;

            let url = `/${category}`;
            if (category === 'search' && query) {
                url = `${url}?query=${encodeURIComponent(query)}`;
            }
            const response = await fetch(url);
            const movies = await response.json();
            
            moviesContainer.innerHTML = movies.map(movie => `
                <div class="movie-card" data-url="${movie.url}">
                    <div class="movie-poster-wrapper">
                        <img src="${movie.poster || '/static/images/no-poster.svg'}" 
                             alt="${movie.title}" 
                             class="movie-poster"
                             onerror="this.src='/static/images/no-poster.svg'">
                    </div>
                    <div class="movie-info">
                        <h3 class="movie-title">${movie.title}</h3>
                        <div class="movie-meta">
                            ${movie.year ? `<span class="movie-year">${movie.year}</span>` : ''}
                            ${movie.rating ? `<span class="movie-rating">${movie.rating}</span>` : ''}
                        </div>
                    </div>
                </div>
            `).join('');

            // Добавляем обработчики для каждой карточки
            document.querySelectorAll('.movie-card').forEach(card => {
                const url = card.dataset.url;

                // Обработчик для всей карточки
                card.addEventListener('click', () => {
                    if (url) {
                        openMovieModal(url);
                    }
                });
            });
            
        } catch (error) {
            console.error('Error loading movies:', error);
            moviesContainer.innerHTML = '<div class="error">Ошибка при загрузке фильмов</div>';
        }
    }

    // Отображение фильмов
    function displayMovies(movies) {
        if (!movies || movies.length === 0) {
            moviesContainer.innerHTML = '<div class="no-results">Ничего не найдено</div>';
            return;
        }
        
        const movieElements = movies.map(movie => `
            <div class="movie-card" data-url="${movie.url}">
                <div class="movie-poster-wrapper">
                    <img src="${movie.poster || '/static/images/no-poster.svg'}" 
                         alt="${movie.title}" 
                         class="movie-poster"
                         onerror="this.src='/static/images/no-poster.svg'">
                    ${movie.quality ? `<div class="movie-quality quality-${movie.quality.toLowerCase()}">${movie.quality}</div>` : ''}
                    <div class="movie-hover-info">
                        <h3 class="movie-title">${movie.title}</h3>
                        <div class="movie-meta">
                            ${movie.year ? `<span class="movie-year">${movie.year}</span>` : ''}
                            ${movie.rating ? `<span class="movie-rating">${movie.rating}</span>` : ''}
                        </div>
                        <button class="watch-button">Смотреть</button>
                    </div>
                </div>
            </div>
        `);
        
        moviesContainer.innerHTML = `
            <div class="movies-grid">
                ${movieElements.join('')}
            </div>
        `;
        
        // Добавляем обработчики для каждой карточки
        document.querySelectorAll('.movie-card').forEach(card => {
            card.addEventListener('click', () => {
                const url = card.dataset.url;
                if (url) {
                    openMovieModal(url);
                }
            });
        });
    }

    // Открытие модального окна с фильмом
    async function openMovieModal(url) {
        try {
            // Показываем статус загрузки
            movieModal.style.display = 'block';
            loadingStatus.style.display = 'flex';
            playerContainer.style.display = 'none';
            
            // Анимируем прогресс
            updateLoadingProgress(30, 'Получение информации о фильме...');
            
            // Получаем информацию о стриме
            const streamResponse = await fetch(`/movie/stream?url=${encodeURIComponent(url)}`);
            const streamData = await streamResponse.json();
            
            if (streamData.error) {
                throw new Error(streamData.error);
            }

            updateLoadingProgress(60, 'Подготовка плеера...');
            
            // Заполняем селект с озвучками
            translationSelect.innerHTML = Object.entries(streamData.translations)
                .map(([name, id]) => `
                    <option value="${id}" ${name === streamData.current_translation ? 'selected' : ''}>
                        ${name}
                    </option>
                `).join('');

            // Заполняем селект с качеством
            const resolutions = streamData.available_resolutions.sort((a, b) => parseInt(b) - parseInt(a));
            qualitySelect.innerHTML = resolutions
                .map(res => `
                    <option value="${res}" ${res === streamData.current_resolution ? 'selected' : ''}>
                        ${res}p
                    </option>
                `).join('');

            // Инициализируем плеер если еще не инициализирован
            if (!player) {
                player = videojs('videoPlayer', {
                    controls: true,
                    fluid: true,
                    playbackRates: [0.5, 1, 1.5, 2],
                    controlBar: {
                        children: [
                            'playToggle',
                            'volumePanel',
                            'currentTimeDisplay',
                            'timeDivider',
                            'durationDisplay',
                            'progressControl',
                            'remainingTimeDisplay',
                            'playbackRateMenuButton',
                            'fullscreenToggle'
                        ]
                    }
                });
            }

            updateLoadingProgress(90, 'Загрузка видео...');

            // Получаем URL для выбранного качества
            const videoUrl = streamData.stream[streamData.current_resolution];

            // Устанавливаем источник видео
            player.src({
                type: 'video/mp4',
                src: videoUrl
            });

            // Сохраняем данные стрима
            currentStreamData = streamData;

            // Показываем плеер
            setTimeout(() => {
                updateLoadingProgress(100, 'Готово!');
                loadingStatus.style.display = 'none';
                playerContainer.style.display = 'block';
            }, 500);

        } catch (error) {
            console.error('Error:', error);
            updateLoadingProgress(100, 'Ошибка при загрузке фильма: ' + error.message);
            setTimeout(() => {
                movieModal.style.display = 'none';
            }, 2000);
        }
    }

    // Обновление видеопотока
    async function updateStream() {
        try {
            updateLoadingProgress(0, 'Изменение параметров...');
            loadingStatus.style.display = 'flex';
            playerContainer.style.display = 'none';
            
            const translation = translationSelect.value;
            const quality = qualitySelect.value;
            
            const response = await fetch(`/movie/stream?url=${encodeURIComponent(currentStreamData.url)}&translation=${translation}&quality=${quality}`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            updateLoadingProgress(50, 'Обновление видеопотока...');
            
            // Запоминаем текущее время воспроизведения
            const currentTime = player.currentTime();
            const wasPlaying = !player.paused();

            // Получаем URL для выбранного качества
            const videoUrl = data.stream[quality];

            // Обновляем источник
            player.src({
                type: 'video/mp4',
                src: videoUrl
            });

            // Восстанавливаем позицию воспроизведения
            player.one('loadedmetadata', function() {
                player.currentTime(currentTime);
                if (wasPlaying) {
                    player.play();
                }
            });

            // Обновляем данные стрима
            currentStreamData = data;

            // Обновляем селект с качеством если изменился список доступных разрешений
            if (data.available_resolutions.length !== qualitySelect.options.length) {
                const resolutions = data.available_resolutions.sort((a, b) => parseInt(b) - parseInt(a));
                qualitySelect.innerHTML = resolutions
                    .map(res => `
                        <option value="${res}" ${res === quality ? 'selected' : ''}>
                            ${res}p
                        </option>
                    `).join('');
            }

            updateLoadingProgress(100, 'Готово!');
            setTimeout(() => {
                loadingStatus.style.display = 'none';
                playerContainer.style.display = 'block';
            }, 500);

        } catch (error) {
            console.error('Error:', error);
            updateLoadingProgress(100, 'Ошибка при изменении параметров: ' + error.message);
            setTimeout(() => {
                loadingStatus.style.display = 'none';
                playerContainer.style.display = 'block';
            }, 2000);
        }
    }

    // Обновление прогресса загрузки
    function updateLoadingProgress(progress, text) {
        const progressFill = loadingStatus.querySelector('.progress-fill');
        const progressText = loadingStatus.querySelector('.progress-text');
        progressFill.style.width = `${progress}%`;
        progressText.textContent = text;
    }

    // Обработчики событий
    translationSelect.addEventListener('change', updateStream);
    qualitySelect.addEventListener('change', updateStream);

    // Закрытие модального окна
    closeModal.addEventListener('click', () => {
        movieModal.style.display = 'none';
        if (player) {
            player.pause();
        }
    });

    // Закрытие модального окна при клике вне его
    window.addEventListener('click', (e) => {
        if (e.target === movieModal) {
            movieModal.style.display = 'none';
            if (player) {
                player.pause();
            }
        }
    });

    // Загружаем фильмы при загрузке страницы
    loadMovies('now');
});
