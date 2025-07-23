"""
Модуль управления конфигурацией проекта.
Реализует паттерн Singleton для глобального доступа к настройкам.
"""
import json
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path


class ConfigManager:
    """Менеджер конфигурации для управления настройками приложения."""
    
    _instance = None
    _config_dir = Path(__file__).parent.parent / 'config'
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._settings = self._load_settings()
            self._channels = self._load_channels()
            self._setup_logging()
            self._initialized = True
    
    def _load_settings(self) -> Dict[str, Any]:
        """Загружает основные настройки из settings.json."""
        settings_path = self._config_dir / 'settings.json'
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Файл настроек не найден: {settings_path}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка парсинга JSON в {settings_path}: {e}")
            raise
    
    def _load_channels(self) -> Dict[str, Any]:
        """Загружает конфигурацию каналов из channels.json."""
        channels_path = self._config_dir / 'channels.json'
        try:
            with open(channels_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Файл каналов не найден: {channels_path}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка парсинга JSON в {channels_path}: {e}")
            raise
    
    def _setup_logging(self) -> None:
        """Настраивает систему логирования."""
        log_config = self._settings.get('logging', {})
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '[%(asctime)s] [%(levelname)s] %(message)s'),
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_config.get('file', 'appointment_bot.log'), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def save_channels_config(self) -> None:
        """Сохраняет изменения в конфигурации каналов."""
        channels_path = self._config_dir / 'channels.json'
        try:
            with open(channels_path, 'w', encoding='utf-8') as f:
                json.dump(self._channels, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Ошибка сохранения конфигурации каналов: {e}")
            raise
    
    @property
    def base_url(self) -> str:
        """Базовый URL API для регистрации."""
        return self._settings.get('base_url', '')
    
    @property
    def site_url(self) -> str:
        """URL сайта для получения JSESSIONID."""
        return self._settings.get('site_url', '')
    
    @property
    def email(self) -> str:
        """Email для регистрации."""
        return self._settings.get('email', '')
    
    @property
    def repeat_minutes(self) -> int:
        """Интервал повтора проверки в минутах."""
        return self._settings.get('repeat_minutes', 30)
    
    @property
    def prefixes(self) -> List[str]:
        """Список префиксов для генерации телефонных номеров."""
        return self._settings.get('prefixes', [])
    
    @property
    def retry_settings(self) -> Dict[str, int]:
        """Настройки повторных попыток."""
        return self._settings.get('retry_settings', {})
    
    @property
    def reset_cycle_enabled(self) -> bool:
        """Включен ли reset-цикл."""
        return self._settings.get('reset_cycle', {}).get('enabled', False)
    
    @property
    def reset_cycle_interval_hours(self) -> int:
        """Интервал reset-цикла в часах."""
        return self._settings.get('reset_cycle', {}).get('interval_hours', 168)
    
    @property
    def reset_cycle_max_future_days(self) -> int:
        """Максимум дней вперед для поиска в reset-цикле."""
        return self._settings.get('reset_cycle', {}).get('max_future_days', 30)
    
    @property
    def reset_cycle_marker_file(self) -> str:
        """Путь к файлу-маркеру reset-цикла."""
        return self._settings.get('reset_cycle', {}).get('marker_file', '/var/lib/appointment-bot/last-reset')

    @property
    def telegram_bot_token(self) -> str:
        """Токен Telegram бота."""
        return self._channels.get('telegram', {}).get('bot_token', '')
    
    @property
    def telegram_enabled(self) -> bool:
        """Включены ли Telegram уведомления."""
        return self._channels.get('telegram', {}).get('enabled', False)
    
    @property
    def channels(self) -> List[Dict[str, Any]]:
        """Список каналов с их настройками."""
        return self._channels.get('channels', [])
    
    def get_channel_by_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Получает канал по ID."""
        for channel in self.channels:
            if channel.get('id') == channel_id:
                return channel
        return None
    
    def update_service_last_date(self, channel_id: str, service_id: str, last_date: str) -> None:
        """Обновляет последнюю дату регистрации для услуги."""
        logging.info(f"Обновление last_registered_date: канал={channel_id}, сервис={service_id}, дата={last_date}")
        
        for channel in self.channels:
            if channel.get('id') == channel_id:
                for service in channel.get('services', []):
                    if service.get('service_id') == service_id:
                        old_date = service.get('last_registered_date', 'не установлена')
                        service['last_registered_date'] = last_date
                        logging.info(f"✓ Дата обновлена: {old_date} → {last_date}")
                        
                        try:
                            self.save_channels_config()
                            logging.info(f"✓ Конфигурация сохранена в файл channels.json")
                        except Exception as e:
                            logging.error(f"✗ Ошибка сохранения конфигурации: {e}")
                            raise
                        return
        logging.warning(f"✗ Услуга {service_id} в канале {channel_id} не найдена") 