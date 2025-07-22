"""
Модуль утилит для работы с данными.
Содержит функции для генерации номеров телефонов и обработки дат.
"""
import random
import time
import asyncio
import aiohttp
import logging
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


def generate_phone(prefixes: List[str]) -> str:
    """
    Генерирует случайный телефонный номер.
    
    Args:
        prefixes: Список доступных префиксов
        
    Returns:
        Сгенерированный номер телефона
    """
    if not prefixes:
        raise ValueError("Список префиксов пуст")
    
    prefix = random.choice(prefixes)
    suffix = ''.join(str(random.randint(0, 9)) for _ in range(6))
    return "48" + prefix + suffix


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


async def retry_request(session: aiohttp.ClientSession, method: str, url: str, 
                       max_retries: int = 5, initial_delay: int = 1, 
                       delay_multiplier: int = 2, **kwargs) -> str:
    """
    Выполняет HTTP запрос с повторными попытками.
    
    Args:
        session: aiohttp сессия
        method: HTTP метод
        url: URL для запроса
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка
        delay_multiplier: Множитель задержки
        **kwargs: Дополнительные параметры для запроса
        
    Returns:
        Ответ сервера в виде текста
    """
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            logging.warning(f"Попытка {attempt + 1}: ошибка запроса к {url}: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay)
            delay *= delay_multiplier
    
    raise Exception(f"Не удалось выполнить запрос к {url} после {max_retries} попыток")


def get_chrome_session(site_url: str) -> tuple:
    """
    Получает JSESSIONID и создает requests сессию.
    
    Args:
        site_url: URL сайта для получения cookies
        
    Returns:
        Кортеж (requests_session, jsessionid)
    """
    import requests
    
    # Настройки Chrome
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    
    # Подавление логов DevTools (обновлено для Selenium 4.x)
    service = Service()
    service.log_output = "/dev/null"
    
    try:
        # Обновлено для Selenium 4.x - используем современный API
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(site_url)
        time.sleep(2)
        
        jsessionid = None
        for cookie in driver.get_cookies():
            if cookie["name"].lower() == "jsessionid":
                jsessionid = cookie["value"]
                break
        
        driver.quit()
        
        if not jsessionid:
            raise Exception("JSESSIONID не найден")
        
        # Создаем requests сессию
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Content-Type": "application/json",
            "Cookie": f"JSESSIONID={jsessionid}",
            "Referer": site_url
        })
        
        logging.info(f"✓ JSESSIONID получен: {jsessionid}")
        return session, jsessionid
        
    except Exception as e:
        logging.error(f"Ошибка получения JSESSIONID: {e}")
        raise


def setup_csrf_token(session, base_url: str) -> str:
    """
    Получает и устанавливает CSRF токен для сессии.
    
    Args:
        session: requests сессия
        base_url: Базовый URL API
        
    Returns:
        CSRF токен
    """
    for attempt in range(3):
        try:
            config = session.get(f"{base_url}/configuration", timeout=10).json()
            csrf_token = config.get('token')
            if csrf_token:
                session.headers["X-Csrf-Token"] = csrf_token
                logging.info(f"✓ X-Csrf-Token получен: {csrf_token}")
                return csrf_token
        except Exception as e:
            logging.warning(f"Попытка {attempt + 1} получения CSRF токена: {e}")
            time.sleep(2)
    
    raise Exception("Не удалось получить CSRF токен") 