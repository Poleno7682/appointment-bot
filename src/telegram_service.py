"""
Сервис для работы с Telegram API.
Поддерживает отправку сообщений в множественные каналы и обработку callback'ов.
"""
import json
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .utils import retry_request_async


@dataclass
class VisitInfo:
    """Информация о визите для Telegram сообщения."""
    service_name: str
    slot_length: int
    date: str
    time: str
    phone: str
    channel_name: str


class TelegramService:
    """Сервис для работы с Telegram Bot API."""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}/"
        self.task_queue = asyncio.Queue()
        self._workers = []
    
    async def start_workers(self, num_workers: int = 3) -> None:
        """Запускает воркеры для обработки callback'ов."""
        self._workers = [
            asyncio.create_task(self._callback_worker()) 
            for _ in range(num_workers)
        ]
        logging.info(f"Запущено {num_workers} воркеров для обработки callback'ов")
    
    async def stop_workers(self) -> None:
        """Останавливает воркеры."""
        await self.task_queue.join()
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()
        logging.info("Воркеры остановлены")
    
    async def _callback_worker(self) -> None:
        """Воркер для обработки callback задач."""
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    task_data = await self.task_queue.get()
                    await self._handle_callback_task(session, task_data)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logging.error(f"Ошибка в callback воркере: {e}")
                finally:
                    self.task_queue.task_done()
    
    async def _handle_callback_task(self, session: aiohttp.ClientSession, 
                                  task_data: Dict[str, Any]) -> None:
        """Обрабатывает задачу callback'а."""
        chat_id = task_data['chat_id']
        message_id = task_data['message_id']
        original_text = task_data['original_text']
        
        new_text = original_text + "\n\nWizyta wykorzystana: ❌Tak"
        url = f"{self.api_url}editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text
        }
        
        try:
            response_text = await retry_request_async(session, "POST", url, data=payload)
            logging.info(f"Callback обработан для сообщения {message_id}")
        except Exception as e:
            logging.error(f"Ошибка при обновлении сообщения {message_id}: {e}")
    
    async def send_visit_notification(self, visit_info: VisitInfo, 
                                    chat_id: str) -> Optional[int]:
        """
        Отправляет уведомление о регистрации визита.
        
        Args:
            visit_info: Информация о визите
            chat_id: ID чата для отправки
            
        Returns:
            ID отправленного сообщения или None при ошибке
        """
        message = self._format_visit_message(visit_info)
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message + "\n\nWizyta wykorzystana: ✅Nie",
                "reply_markup": json.dumps({
                    "inline_keyboard": [[
                        {"text": "Wykorzystać wizytę", "callback_data": "mark_used"}
                    ]]
                })
            }
            
            try:
                response_text = await retry_request_async(session, "POST", url, data=payload)
                response_data = json.loads(response_text)
                
                if response_data.get('ok'):
                    message_id = response_data['result']['message_id']
                    logging.info(f"Уведомление отправлено в {chat_id}, message_id: {message_id}")
                    return message_id
                else:
                    logging.error(f"Ошибка отправки в Telegram: {response_data}")
                    return None
                    
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления в {chat_id}: {e}")
                return None
    
    def _format_visit_message(self, visit_info: VisitInfo) -> str:
        """Форматирует сообщение о визите."""
        return (
            f"📣 Wizyta zarejestrowana\n"
            f"✔️ Sprawa: {visit_info.service_name}\n"
            f"⏩ Długość: {visit_info.slot_length} minut\n"
            f"📅 Data: {visit_info.date}\n"
            f"🕗 Godzina: {visit_info.time}\n"
            f"📞 Numer: {visit_info.phone}"
        )
    
    async def poll_updates(self) -> None:
        """Основной цикл опроса обновлений от Telegram."""
        last_update_id = 0
        logging.info("Запуск опроса Telegram обновлений...")
        
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    url = f"{self.api_url}getUpdates"
                    params = {"offset": last_update_id + 1, "timeout": 10}
                    
                    async with session.get(url, params=params) as response:
                        response.raise_for_status()
                        data = await response.json()
                    
                    for update in data.get("result", []):
                        last_update_id = update["update_id"]
                        
                        if "callback_query" in update:
                            await self._process_callback_query(session, update["callback_query"])
                
                except Exception as e:
                    logging.warning(f"Ошибка при получении обновлений: {e}")
                    await asyncio.sleep(10)
                
                await asyncio.sleep(1)
    
    async def _process_callback_query(self, session: aiohttp.ClientSession, 
                                    callback: Dict[str, Any]) -> None:
        """Обрабатывает callback query."""
        message_id = callback["message"]["message_id"]
        original_text = callback["message"]["text"].split("\n\n")[0]
        chat_id = callback["message"]["chat"]["id"]
        
        # Добавляем задачу в очередь
        await self.task_queue.put({
            'chat_id': chat_id,
            'message_id': message_id,
            'original_text': original_text
        })
        
        # Подтверждаем callback
        try:
            await retry_request_async(
                session,
                "POST",
                f"{self.api_url}answerCallbackQuery",
                data={"callback_query_id": callback["id"]}
            )
        except Exception as e:
            logging.error(f"Ошибка подтверждения callback: {e}")
    
    async def send_error_notification(self, error_message: str, chat_id: str) -> None:
        """Отправляет уведомление об ошибке."""
        message = f"⚠️ Błąd w systemie rejestracji:\n{error_message}"
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message
            }
            
            try:
                await retry_request_async(session, "POST", url, data=payload)
                logging.info(f"Уведомление об ошибке отправлено в {chat_id}")
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления об ошибке: {e}") 