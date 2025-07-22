"""
Утилиты для работы с веб-автоматизацией и HTTP запросами
"""
import time
import random
import requests
import subprocess
import os
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def generate_phone():
    """Генерирует случайный номер телефона"""
    prefixes = ["733", "668", "883", "602", "690", "577", "886", "880", "517", "784", "793", "697", "510", "881", "575"]
    prefix = random.choice(prefixes)
    number = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"{prefix}{number}"


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
        print(f"Ошибка получения JSESSIONID: {e}")
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
            print(f"WARNING: ChromeDriver {chromedriver_version} may not be compatible with Chrome {chrome_version}")
            return False
            
        return True
        
    except Exception as e:
        print(f"Ошибка проверки совместимости: {e}")
        return False 