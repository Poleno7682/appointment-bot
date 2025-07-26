"""
Утилиты для работы с веб-автоматизацией и HTTP запросами
"""
import time
import random
import requests
import subprocess
import os
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def generate_phone(prefixes: List[str] = None) -> str:
    """
    Генерирует случайный телефонный номер.
    
    Args:
        prefixes: Список доступных префиксов (опционально)
        
    Returns:
        Сгенерированный номер телефона
    """
    if not prefixes:
        prefixes = ["733", "668", "883", "602", "690", "577", "886", "880", "517", "784", "793", "697", "510", "881", "575"]
    
    prefix = random.choice(prefixes)
    number = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"48{prefix}{number}"


def find_next_dates(dates: List[dict], last_date: Optional[str]) -> List[str]:
    """
    Находит следующие доступные даты после указанной.
    
    Args:
        dates: Список дат от API
        last_date: Последняя зарегистрированная дата
        
    Returns:
        Список доступных дат
    """
    return [d["date"] for d in dates if not last_date or d["date"] > last_date]


def filter_dates_by_week(dates, target_week):
    """Фильтрует даты по номеру недели"""
    return [date for date in dates if date.get("week") == target_week]


def retry_request(func, *args, max_retries=5, initial_delay=1, delay_multiplier=2, **kwargs):
    """Повторяет запрос с экспоненциальной задержкой при ошибке"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = initial_delay * (delay_multiplier ** attempt)
            time.sleep(delay + random.uniform(0, 1))


async def retry_request_async(session: aiohttp.ClientSession, method: str, url: str, 
                       max_retries: int = 5, initial_delay: int = 1, 
                       delay_multiplier: int = 2, **kwargs) -> str:
    """
    Выполняет асинхронный HTTP запрос с повторными попытками при ошибке.
    
    Args:
        session: Сессия aiohttp
        method: HTTP метод
        url: URL для запроса
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка в секундах
        delay_multiplier: Множитель задержки
        **kwargs: Дополнительные параметры для запроса
        
    Returns:
        Ответ сервера в виде строки
        
    Raises:
        Exception: Если все попытки неудачны
    """
    for attempt in range(max_retries):
        try:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Все попытки исчерпаны для {method} {url}: {e}")
                raise e
            
            delay = initial_delay * (delay_multiplier ** attempt)
            logging.warning(f"Попытка {attempt + 1} неудачна для {method} {url}: {e}. Повтор через {delay}с")
            await asyncio.sleep(delay + random.uniform(0, 1))


def get_jsessionid_and_csrf(site_url: str) -> Optional[Dict[str, str]]:
    """
    Получает JSESSIONID и CSRF токен с помощью Selenium
    
    Args:
        site_url: URL сайта для получения сессии
        
    Returns:
        Словарь с jsessionid и csrf_token или None при ошибке
    """
    try:
        # Настройки Chrome
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        
        # Настройка службы ChromeDriver (исправлено для Selenium 4.x)
        service = Service()
        
        # Подавление логов ChromeDriver - правильный способ для Selenium 4.x
        with open(os.devnull, 'w') as devnull:
            service.log_output = devnull
            
            # Создание драйвера
            driver = webdriver.Chrome(service=service, options=options)
            
            try:
                # Переход на сайт
                driver.get(site_url)
                
                # Ожидание загрузки страницы
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Получение cookies
                cookies = driver.get_cookies()
                jsessionid = None
                
                for cookie in cookies:
                    if cookie['name'] == 'JSESSIONID':
                        jsessionid = cookie['value']
                        break
                
                # Поиск CSRF токена в мета-тегах или скрытых полях
                csrf_token = None
                try:
                    # Поиск в мета-тегах
                    csrf_element = driver.find_element(By.NAME, "_csrf_token")
                    csrf_token = csrf_element.get_attribute("content")
                except:
                    try:
                        # Поиск в скрытых полях формы
                        csrf_element = driver.find_element(By.NAME, "_token")
                        csrf_token = csrf_element.get_attribute("value")
                    except:
                        pass
                
                if jsessionid:
                    return {
                        "jsessionid": jsessionid,
                        "csrf_token": csrf_token
                    }
                    
            finally:
                driver.quit()
                
    except Exception as e:
        logging.error(f"Ошибка получения JSESSIONID: {e}")
        return None


def create_session_with_jsessionid(jsessionid: str, csrf_token: Optional[str] = None) -> requests.Session:
    """
    Создает HTTP сессию с полученным JSESSIONID
    
    Args:
        jsessionid: ID сессии
        csrf_token: CSRF токен (опционально)
        
    Returns:
        Настроенная сессия requests
    """
    session = requests.Session()
    
    # Устанавливаем cookie
    session.cookies.set('JSESSIONID', jsessionid)
    
    # Настраиваем заголовки
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9,pl;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    })
    
    # Добавляем CSRF токен если есть
    if csrf_token:
        session.headers.update({
            'X-CSRF-TOKEN': csrf_token,
            'X-XSRF-TOKEN': csrf_token
        })
    
    return session


def check_chromedriver_compatibility():
    """Проверяет совместимость ChromeDriver с установленным Chrome"""
    try:
        # Получаем версию Chrome
        chrome_version = subprocess.check_output(['google-chrome', '--version'], text=True).strip()
        chrome_version = chrome_version.split()[-1]
        
        # Получаем версию ChromeDriver
        chromedriver_version = subprocess.check_output(['chromedriver', '--version'], text=True).strip()
        chromedriver_version = chromedriver_version.split()[1]
        
        chrome_major = chrome_version.split('.')[0]
        chromedriver_major = chromedriver_version.split('.')[0]
        
        if chrome_major != chromedriver_major:
            logging.warning(f"ChromeDriver {chromedriver_version} may not be compatible with Chrome {chrome_version}")
            return False
            
        return True
        
    except Exception as e:
        logging.error(f"Ошибка проверки совместимости: {e}")
        return False


# ФУНКЦИИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
def get_chrome_session(site_url: str) -> tuple:
    """
    Обратная совместимость: получает JSESSIONID и создает requests сессию.
    
    Args:
        site_url: URL сайта для получения cookies
        
    Returns:
        Кортеж (requests_session, jsessionid)
    """
    session_data = get_jsessionid_and_csrf(site_url)
    if not session_data:
        raise Exception("Не удалось получить JSESSIONID")
        
    jsessionid = session_data['jsessionid']
    session = create_session_with_jsessionid(jsessionid, session_data.get('csrf_token'))
    
    logging.info(f"✓ JSESSIONID получен: {jsessionid}")
    return session, jsessionid


def setup_csrf_token(session, base_url: str) -> str:
    """
    Обратная совместимость: получает и устанавливает CSRF токен для сессии.
    
    Args:
        session: requests сессия
        base_url: Базовый URL API
        
    Returns:
        CSRF токен
    """
    for attempt in range(3):
        try:
            config = session.get(f"{base_url}/configuration", timeout=30).json()
            csrf_token = config.get('token')
            if csrf_token:
                session.headers["X-Csrf-Token"] = csrf_token
                logging.info(f"✓ X-Csrf-Token получен: {csrf_token}")
                return csrf_token
        except Exception as e:
            logging.warning(f"Попытка {attempt + 1} получения CSRF токена: {e}")
            time.sleep(2)
    
    raise Exception("Не удалось получить CSRF токен") 


# 🔄 RESET-ЦИКЛ УТИЛИТЫ

def should_run_reset_cycle(marker_file: str, interval_hours: int) -> bool:
    """
    Определяет нужно ли запускать reset-цикл на основе файла-маркера.
    
    Args:
        marker_file: Путь к файлу-маркеру
        interval_hours: Интервал в часах между reset-циклами
        
    Returns:
        True если пора запускать reset-цикл
    """
    import os
    import time
    
    interval_seconds = interval_hours * 3600
    
    try:
        if not os.path.exists(marker_file):
            # Первый запуск - создаем файл и запускаем reset-цикл
            create_reset_marker(marker_file)
            logging.info(f"🔄 Создан файл-маркер reset-цикла: {marker_file}")
            return True
        
        # Проверяем время последней модификации
        last_reset = os.path.getmtime(marker_file)
        current_time = time.time()
        elapsed_hours = (current_time - last_reset) / 3600
        
        if (current_time - last_reset) >= interval_seconds:
            # Время пришло - обновляем файл
            update_reset_marker(marker_file)
            logging.info(f"🔄 Reset-цикл triggered после {elapsed_hours:.1f} часов")
            return True
        
        next_reset_hours = interval_hours - elapsed_hours
        logging.debug(f"🔄 Reset-цикл через {next_reset_hours:.1f} часов")
        return False
        
    except Exception as e:
        logging.error(f"Ошибка проверки reset-цикла: {e}")
        return False


def create_reset_marker(marker_file: str) -> None:
    """Создает файл-маркер reset-цикла."""
    import os
    
    try:
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(marker_file), exist_ok=True)
        
        # Создаем файл
        with open(marker_file, 'w') as f:
            f.write(f"Reset cycle marker created at {time.time()}\n")
            
        logging.info(f"✓ Создан файл-маркер: {marker_file}")
        
    except Exception as e:
        logging.error(f"Ошибка создания файла-маркера {marker_file}: {e}")


def update_reset_marker(marker_file: str) -> None:
    """Обновляет время файла-маркера reset-цикла."""
    import os
    
    try:
        # Обновляем время модификации файла
        if os.path.exists(marker_file):
            os.utime(marker_file, None)  # Устанавливает текущее время
        else:
            create_reset_marker(marker_file)
            
        logging.info(f"✓ Обновлен файл-маркер: {marker_file}")
        
    except Exception as e:
        logging.error(f"Ошибка обновления файла-маркера {marker_file}: {e}")


def get_server_current_date() -> str:
    """
    Получает текущую дату сервера в формате YYYY-MM-DD.
    
    Returns:
        Текущая дата в формате YYYY-MM-DD
    """
    from datetime import datetime
    
    try:
        # Используем локальное время сервера
        current_date = datetime.now().strftime('%Y-%m-%d')
        logging.debug(f"🗓️ Текущая дата сервера: {current_date}")
        return current_date
        
    except Exception as e:
        logging.error(f"Ошибка получения даты сервера: {e}")
        return datetime.now().strftime('%Y-%m-%d')


def find_dates_from_date(dates: List[dict], start_date: str, max_future_days: int = 30) -> List[str]:
    """
    Находит доступные даты начиная с указанной даты (для reset-цикла).
    ИСКЛЮЧАЕТ прошлые даты и слишком близкие к текущему времени.
    
    Args:
        dates: Список дат от API
        start_date: Дата начала поиска
        max_future_days: Максимум дней вперед
        
    Returns:
        Список доступных дат (только будущие)
    """
    from datetime import datetime, timedelta
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        current_dt = datetime.now()
        
        # 🔑 ИСПРАВЛЕНИЕ: Используем дату не раньше завтрашнего дня
        min_date = max(start_dt, current_dt + timedelta(days=1))
        min_date_str = min_date.strftime('%Y-%m-%d')
        
        max_date = start_dt + timedelta(days=max_future_days)
        max_date_str = max_date.strftime('%Y-%m-%d')
        
        # 🔑 СТРОГО БОЛЬШЕ ИЛИ РАВНО минимальной дате (завтра+)
        filtered_dates = [
            d["date"] for d in dates 
            if min_date_str <= d["date"] <= max_date_str
        ]
        
        logging.debug(f"🔍 Reset-цикл: найдено {len(filtered_dates)} дат с {min_date_str} по {max_date_str} (исключены прошлые даты)")
        return filtered_dates
        
    except Exception as e:
        logging.error(f"Ошибка фильтрации дат для reset-цикла: {e}")
        return [] 