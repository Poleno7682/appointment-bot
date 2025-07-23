#!/usr/bin/env python3
"""
Appointment Bot - Автоматическая регистрация визитов в системе онлайн-записи.
Главный файл приложения.
"""
import asyncio
import logging
import signal
import sys
from typing import Optional

from src.config_manager import ConfigManager
from src.telegram_service import TelegramService
from src.appointment_service import AppointmentService


class AppointmentBot:
    """Основной класс приложения."""
    
    def __init__(self):
        self.config = ConfigManager()
        self.telegram_service: Optional[TelegramService] = None
        self.appointment_service: Optional[AppointmentService] = None
        self.running = False
        self._tasks = []
    
    async def initialize(self) -> None:
        """Инициализирует все сервисы."""
        try:
            # Проверяем настройки Telegram
            if not self.config.telegram_enabled:
                logging.warning("Telegram уведомления отключены")
                return
            
            if not self.config.telegram_bot_token:
                logging.error("Telegram bot token не настроен")
                sys.exit(1)
            
            # Инициализируем сервисы
            self.telegram_service = TelegramService(self.config.telegram_bot_token)
            self.appointment_service = AppointmentService(self.config, self.telegram_service)
            
            # Запускаем воркеры Telegram
            await self.telegram_service.start_workers()
            
            logging.info("✓ Все сервисы инициализированы успешно")
            
        except Exception as e:
            logging.error(f"Ошибка инициализации: {e}")
            sys.exit(1)
    
    async def start_appointment_worker(self) -> None:
        """Запускает воркер регистрации визитов."""
        logging.info("Запуск воркера регистрации визитов...")
        
        while self.running:
            try:
                await self.appointment_service.process_all_services()
                logging.info(f"Следующая проверка через {self.config.repeat_minutes} минут...")
                
                # Ждем с проверкой флага running каждую секунду
                for _ in range(self.config.repeat_minutes * 60):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logging.error(f"Ошибка в воркере регистрации: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    async def start_telegram_polling(self) -> None:
        """Запускает опрос Telegram обновлений."""
        if self.telegram_service:
            await self.telegram_service.poll_updates()
    
    async def run(self) -> None:
        """Запускает основной цикл приложения."""
        self.running = True
        
        try:
            # Создаем задачи
            appointment_task = asyncio.create_task(self.start_appointment_worker())
            telegram_task = asyncio.create_task(self.start_telegram_polling())
            
            self._tasks = [appointment_task, telegram_task]
            
            logging.info("🚀 Appointment Bot запущен")
            logging.info(f"Настроено каналов: {len(self.config.channels)}")
            logging.info(f"Интервал проверки: {self.config.repeat_minutes} минут")
            
            # Ждем завершения любой задачи
            done, pending = await asyncio.wait(
                self._tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Отменяем незавершенные задачи
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            logging.error(f"Критическая ошибка в основном цикле: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Корректно завершает работу приложения."""
        logging.info("Завершение работы...")
        self.running = False
        
        # Останавливаем Telegram воркеры
        if self.telegram_service:
            await self.telegram_service.stop_workers()
        
        # Отменяем все задачи
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logging.info("✓ Приложение завершено")
    
    def handle_signal(self, signum, frame) -> None:
        """Обработчик сигналов для корректного завершения."""
        logging.info(f"Получен сигнал {signum}, завершение работы...")
        self.running = False


async def main():
    """Главная функция приложения."""
    bot = AppointmentBot()
    
    # Настраиваем обработчики сигналов
    signal.signal(signal.SIGINT, bot.handle_signal)
    signal.signal(signal.SIGTERM, bot.handle_signal)
    
    try:
        await bot.initialize()
        await bot.run()
    except KeyboardInterrupt:
        logging.info("Получен сигнал прерывания")
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Приложение прервано пользователем")
    except Exception as e:
        logging.error(f"Фатальная ошибка: {e}")
        sys.exit(1) 