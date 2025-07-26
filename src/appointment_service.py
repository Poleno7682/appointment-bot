"""
Сервис регистрации визитов.
Основная бизнес-логика для автоматической регистрации визитов в системе онлайн-записи.
"""
import json
import time
import random
import logging
from typing import Dict, Any, List, Optional
import requests
from dataclasses import dataclass

from .config_manager import ConfigManager
from .telegram_service import TelegramService, VisitInfo
from .utils import (
    generate_phone, find_next_dates, get_chrome_session, setup_csrf_token,
    get_server_current_date, find_dates_from_date
)


@dataclass
class ServiceEntry:
    """Данные услуги для регистрации."""
    branch_name: str
    branch_id: str
    service_name: str
    service_id: str
    qp_id: str
    adult: int
    visits_per_day: int
    last_registered_date: Optional[str]


class AppointmentService:
    """Сервис для автоматической регистрации визитов в системе онлайн-записи."""
    
    def __init__(self, config_manager: ConfigManager, telegram_service: TelegramService):
        self.config = config_manager
        self.telegram = telegram_service
        self._session = None
    
    def _create_session(self) -> requests.Session:
        """Создает новую сессию с JSESSIONID и CSRF токеном."""
        try:
            session, jsessionid = get_chrome_session(self.config.site_url)
            setup_csrf_token(session, self.config.base_url)
            logging.info("✓ Сессия создана успешно")
            return session
        except Exception as e:
            logging.error(f"Ошибка создания сессии: {e}")
            raise
    
    def _get_service_details(self, session: requests.Session, 
                           service_entry: ServiceEntry) -> Optional[Dict[str, Any]]:
        """Получает детали услуги от API."""
        try:
            url = f"{self.config.base_url}/branches/{service_entry.branch_id}/services;validate=true"
            full_services = session.get(url, timeout=30).json()
            
            service = next(
                (s for s in full_services if s["publicId"] == service_entry.service_id), 
                None
            )
            
            if not service:
                logging.warning(f"Услуга {service_entry.service_name} не найдена")
                return None
                
            return service
            
        except Exception as e:
            logging.error(f"Ошибка получения деталей услуги {service_entry.service_name}: {e}")
            return None
    
    def _get_available_dates(self, session: requests.Session, 
                           service_entry: ServiceEntry, slot_length: int) -> List[str]:
        """Получает доступные даты для услуги."""
        try:
            url = (f"{self.config.base_url}/branches/{service_entry.branch_id}/dates;"
                  f"servicePublicId={service_entry.service_id};"
                  f"customSlotLength={slot_length}")
            
            dates = session.get(url, timeout=30).json()
            filtered_dates = find_next_dates(dates, service_entry.last_registered_date)
            
            # Базовая информация о результатах поиска дат
            if filtered_dates:
                logging.info(f"[{service_entry.service_name}] Найдено {len(filtered_dates)} доступных дат")
            
            return filtered_dates
            
        except Exception as e:
            logging.error(f"Ошибка получения дат для {service_entry.service_name}: {e}")
            return []
    
    def _get_available_times(self, session: requests.Session, 
                           service_entry: ServiceEntry, date: str, 
                           slot_length: int) -> List[Dict[str, Any]]:
        """Получает доступные времена для указанной даты."""
        try:
            url = (f"{self.config.base_url}/branches/{service_entry.branch_id}/dates/{date}/times;"
                  f"servicePublicId={service_entry.service_id};"
                  f"customSlotLength={slot_length}")
            
            return session.get(url, timeout=30).json()
            
        except Exception as e:
            logging.error(f"Ошибка получения времен для {date}: {e}")
            return []
    
    def _reserve_appointment(self, session: requests.Session, 
                           service_entry: ServiceEntry, date: str, 
                           time_slot: str, slot_length: int) -> Optional[str]:
        """Резервирует время для записи."""
        try:
            url = (f"{self.config.base_url}/branches/{service_entry.branch_id}/dates/{date}/times/{time_slot}/reserve;"
                  f"customSlotLength={slot_length}")
            
            people_services = [{
                "publicId": service_entry.service_id,
                "qpId": service_entry.qp_id,
                "adult": service_entry.adult,
                "name": service_entry.service_name,
                "child": 0
            }]
            
            payload = {
                "services": [{"publicId": service_entry.service_id}],
                "custom": json.dumps({"peopleServices": people_services})
            }
            
            response = session.post(url, json=payload, timeout=30)
            reserve_data = response.json()
            
            appointment_id = (reserve_data.get("publicId") or 
                            reserve_data.get("value", {}).get("publicId"))
            
            if appointment_id:
                logging.info(f"✓ Время {time_slot} зарезервировано: {appointment_id}")
                return appointment_id
            else:
                return None
                
        except Exception as e:
            logging.error(f"Ошибка резервирования {time_slot}: {e}")
            return None
    
    def _create_customer(self, session: requests.Session, phone: str) -> None:
        """Создает записи клиента в системе."""
        try:
            customer = {
                "email": self.config.email,
                "phone": phone,
                "firstName": "",
                "lastName": "",
                "dateOfBirth": "",
                "externalId": "",
                "addressLine1": "",
                "addressLine2": "",
                "addressCity": "",
                "addressZip": "",
                "addressState": "",
                "addressCountry": "",
                "custom": "{}"
            }
            
            url = f"{self.config.base_url}/matchCustomer"
            session.post(url, json=customer, timeout=30)
            
        except Exception as e:
            logging.error(f"Ошибка создания клиента: {e}")
            raise
    
    def _confirm_appointment(self, session: requests.Session, 
                           appointment_id: str, service_entry: ServiceEntry, 
                           phone: str, slot_length: int) -> bool:
        """Подтверждает запись."""
        try:
            people_services = [{
                "publicId": service_entry.service_id,
                "qpId": service_entry.qp_id,
                "adult": service_entry.adult,
                "name": service_entry.service_name,
                "child": 0
            }]
            
            confirm_payload = {
                "customer": {
                    "email": self.config.email,
                    "phone": phone,
                    "firstName": "",
                    "lastName": "",
                    "dateOfBirth": "",
                    "externalId": "",
                    "addressLine1": "",
                    "addressLine2": "",
                    "addressCity": "",
                    "addressZip": "",
                    "addressState": "",
                    "addressCountry": "",
                    "custom": "{}"
                },
                "languageCode": "pl",
                "countryCode": "pl",
                "captcha": "",
                "custom": json.dumps({
                    "peopleServices": people_services,
                    "totalCost": 0,
                    "createdByUser": "Qmatic Web Booking",
                    "paymentRef": "",
                    "customSlotLength": slot_length
                }),
                "notes": "",
                "title": "Qmatic Web Booking",
                "notificationType": "both"
            }
            
            url = f"{self.config.base_url}/appointments/{appointment_id}/confirm"
            response = session.post(url, json=confirm_payload, timeout=30)
            
            return response.status_code == 200
            
        except Exception as e:
            logging.error(f"Ошибка подтверждения записи {appointment_id}: {e}")
            return False
    
    async def register_visit(self, service_entry: ServiceEntry, 
                           channel_id: str, channel_name: str, 
                           chat_id: str) -> bool:
        """
        Регистрирует визит для конкретной услуги.
        
        Args:
            service_entry: Данные услуги
            channel_id: ID канала
            channel_name: Название канала
            chat_id: ID чата для уведомлений
            
        Returns:
            True если регистрация успешна
        """
        # 🔍 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ о сервисе
        logging.info(f"🔍 Обработка сервиса: {service_entry.service_name} (adult={service_entry.adult}, last_date={service_entry.last_registered_date})")
        
        if not self._session:
            self._session = self._create_session()
        
        # Получаем детали услуги
        service_details = self._get_service_details(self._session, service_entry)
        if not service_details:
            return False
        
        # Вычисляем длительность слота
        duration = int(service_details.get("duration", 20))
        additional = int(service_details.get("additionalDuration", 10))
        slot_length = duration + additional * (service_entry.adult - 1)
        
        # Получаем доступные даты
        available_dates = self._get_available_dates(self._session, service_entry, slot_length)
        if not available_dates:
            logging.info(f"[{service_entry.service_name}] Нет доступных дат после {service_entry.last_registered_date}")
            return False
        
        total_attempts = 0
        total_successes = 0
        last_processed_date = None
        
        # Пробуем зарегистрироваться на ближайшие даты
        for date in available_dates:
            times = self._get_available_times(self._session, service_entry, date, slot_length)
            if not times:
                # Если нет доступных времен, запоминаем эту дату но НЕ обновляем сразу
                logging.info(f"[{service_entry.service_name}] Нет времен на {date}")
                last_processed_date = date
                continue
            
            successful_registrations = 0
            times_copy = times[:]
            
            while successful_registrations < service_entry.visits_per_day and times_copy:
                time_data = random.choice(times_copy)
                times_copy.remove(time_data)
                time_slot = time_data["time"]
                total_attempts += 1
                
                # Резервируем время
                appointment_id = self._reserve_appointment(
                    self._session, service_entry, date, time_slot, slot_length
                )
                
                if not appointment_id:
                    continue
                
                # Генерируем номер телефона
                phone = generate_phone(self.config.prefixes)
                
                # Создаем клиента
                try:
                    self._create_customer(self._session, phone)
                except Exception as e:
                    logging.error(f"Ошибка создания клиента: {e}")
                    continue
                
                # Подтверждаем запись
                if self._confirm_appointment(self._session, appointment_id, service_entry, phone, slot_length):
                    successful_registrations += 1
                    total_successes += 1
                    logging.info(f"✓ Визит зарегистрирован: {date} {time_slot} | {phone}")
                    
                    # Отправляем уведомление в Telegram
                    if self.config.telegram_enabled:
                        visit_info = VisitInfo(
                            service_name=service_entry.service_name,
                            slot_length=slot_length,
                            date=date,
                            time=time_slot,
                            phone=phone,
                            channel_name=channel_name
                        )
                        
                        await self.telegram.send_visit_notification(visit_info, chat_id)
                    
                    # 🔑 ЗАПОМИНАЕМ ДАТУ но НЕ обновляем сразу в конфиге
                    last_processed_date = date
                    
                    # ✅ ПРОВЕРЯЕМ: достигнут ли лимит на день?
                    if successful_registrations >= service_entry.visits_per_day:
                        logging.info(f"🎯 Лимит {service_entry.visits_per_day} визитов достигнут на {date}")
                        break  # Переходим к следующей дате
                else:
                    logging.warning(f"Ошибка подтверждения записи для {time_slot}")
                
                # Задержка между попытками
                time.sleep(random.uniform(5, 10))
            
            # Если на дате были регистрации или не осталось времен - запоминаем дату
            if successful_registrations > 0 or not times_copy:
                last_processed_date = date
                if successful_registrations < service_entry.visits_per_day and not times_copy:
                    logging.info(f"⚠️ На {date} зарегистрировано только {successful_registrations}/{service_entry.visits_per_day} визитов (нет больше времен)")
            
            # ✅ ЕСЛИ БЫЛИ РЕГИСТРАЦИИ, можем прервать цикл
            if successful_registrations > 0:
                break
        
        # 🔑 ОБНОВЛЯЕМ last_registered_date ТОЛЬКО В КОНЦЕ, если были регистрации
        if total_successes > 0 and last_processed_date:
            self.config.update_service_last_date(channel_id, service_entry.service_id, last_processed_date)
            
            # Показываем статистику для этой услуги
            if total_attempts > total_successes:
                logging.info(f"📊 [{service_entry.service_name}] Статистика: {total_successes}/{total_attempts} успешных резерваций")
            return True
        
        # Показываем итоговую статистику если не было успехов
        if total_attempts > 0:
            logging.info(f"📊 [{service_entry.service_name}] Все слоты заняты: 0/{total_attempts} резерваций")
        
        return False
    
    async def process_all_services(self) -> None:
        """Обрабатывает все услуги во всех каналах."""
        for channel in self.config.channels:
            channel_id = channel['id']
            channel_name = channel['name']
            chat_id = channel['chat_id']
            
            logging.info(f"Обработка канала: {channel_name}")
            
            for service_data in channel.get('services', []):
                try:
                    service_entry = ServiceEntry(
                        branch_name=service_data['branch_name'],
                        branch_id=service_data['branch_id'],
                        service_name=service_data['service_name'],
                        service_id=service_data['service_id'],
                        qp_id=service_data['qpId'],
                        adult=service_data['adult'],
                        visits_per_day=service_data['visits_per_day'],
                        last_registered_date=service_data.get('last_registered_date')
                    )
                    
                    await self.register_visit(service_entry, channel_id, channel_name, chat_id)
                    
                except Exception as e:
                    error_msg = f"Ошибка обработки услуги {service_data.get('service_name', 'Unknown')}: {e}"
                    logging.error(error_msg)
                    
                    if self.config.telegram_enabled:
                        await self.telegram.send_error_notification(error_msg, chat_id)
        
        # Обновляем сессию для следующего цикла
        self._session = None
    
    # 🔄 RESET-ЦИКЛ МЕТОДЫ
    
    async def register_visit_from_date(self, service_entry: ServiceEntry, 
                                      channel_id: str, channel_name: str, 
                                      chat_id: str, start_date: str,
                                      max_future_days: int = 30) -> bool:
        """
        Регистрирует визиты начиная с указанной даты (для reset-цикла).
        НЕ обновляет last_registered_date в конфигурации!
        
        Args:
            service_entry: Данные услуги
            channel_id: ID канала
            channel_name: Название канала
            chat_id: ID чата для уведомлений
            start_date: Дата начала поиска (YYYY-MM-DD)
            max_future_days: Максимум дней вперед для поиска
            
        Returns:
            True если найдены и зарегистрированы визиты
        """
        # 🔑 ПРИНУДИТЕЛЬНО создаем НОВУЮ сессию для каждого сервиса в RESET-цикле
        # Это предотвращает ERROR_SESSION_VIOLATION из-за устаревших токенов
        if self._session:
            self._session.close()
        self._session = self._create_session()
        
        logging.info(f"🔄 [RESET] Начало reset-цикла для {service_entry.service_name} с {start_date}")
        
        # Получаем детали услуги
        service_details = self._get_service_details(self._session, service_entry)
        if not service_details:
            return False
        
        # Вычисляем длительность слота
        duration = int(service_details.get("duration", 20))
        additional = int(service_details.get("additionalDuration", 10))
        slot_length = duration + additional * (service_entry.adult - 1)
        
        # Получаем доступные даты начиная с start_date
        available_dates = self._get_available_dates_from_date(
            self._session, service_entry, slot_length, start_date, max_future_days
        )
        
        if not available_dates:
            logging.info(f"🔄 [RESET] Нет доступных дат для {service_entry.service_name} с {start_date}")
            return False
        
        logging.info(f"🔄 [RESET] Найдено {len(available_dates)} дат для проверки")
        total_registered = 0
        total_attempts = 0
        
        # Пробуем зарегистрироваться на найденные даты
        for date in available_dates:
            times = self._get_available_times(self._session, service_entry, date, slot_length)
            if not times:
                logging.info(f"🔄 [RESET] Нет доступных времен на {date}")
                continue
            
            logging.info(f"🔄 [RESET] Проверяем {date}: найдено {len(times)} доступных времен")
            
            successful_registrations = 0
            times_copy = times[:]
            
            while successful_registrations < service_entry.visits_per_day and times_copy:
                time_data = random.choice(times_copy)
                times_copy.remove(time_data)
                time_slot = time_data["time"]
                total_attempts += 1
                
                logging.debug(f"🔄 [RESET] Попытка {total_attempts}: резервирование {date} {time_slot}")
                
                # Резервируем время
                appointment_id = self._reserve_appointment(
                    self._session, service_entry, date, time_slot, slot_length
                )
                
                if not appointment_id:
                    continue
                
                # Генерируем номер телефона
                phone = generate_phone(self.config.prefixes)
                
                # Создаем клиента
                try:
                    self._create_customer(self._session, phone)
                except Exception as e:
                    logging.error(f"Ошибка создания клиента: {e}")
                    continue
                
                # Подтверждаем запись
                if self._confirm_appointment(self._session, appointment_id, service_entry, phone, slot_length):
                    successful_registrations += 1
                    total_registered += 1
                    logging.info(f"✓ [RESET] Визит зарегистрирован: {date} {time_slot} | {phone}")
                    
                    # 🔑 ОТПРАВЛЯЕМ ОБЫЧНЫЕ TELEGRAM УВЕДОМЛЕНИЯ (без изменений)
                    if self.config.telegram_enabled:
                        visit_info = VisitInfo(
                            service_name=service_entry.service_name,
                            slot_length=slot_length,
                            date=date,
                            time=time_slot,
                            phone=phone,
                            channel_name=channel_name
                        )
                        
                        await self.telegram.send_visit_notification(visit_info, chat_id)
                    
                    # Проверяем лимит на день
                    if successful_registrations >= service_entry.visits_per_day:
                        logging.info(f"🔄 [RESET] Лимит {service_entry.visits_per_day} визитов достигнут на {date}")
                        break
                else:
                    logging.warning(f"Ошибка подтверждения записи для {time_slot}")
                
                # Задержка между попытками
                time.sleep(random.uniform(5, 10))
        
        if total_registered > 0:
            logging.info(f"🔄 [RESET] Завершен reset-цикл: зарегистрировано {total_registered} визитов для {service_entry.service_name}")
            if total_attempts > total_registered:
                logging.info(f"📊 [RESET] Статистика: {total_registered}/{total_attempts} успешных резерваций")
            return True
        else:
            if total_attempts > 0:
                success_rate = (total_registered / total_attempts) * 100
                logging.info(f"📊 [RESET] Все слоты заняты: {total_registered}/{total_attempts} попыток ({success_rate:.1f}% успешных) для {service_entry.service_name}")
                logging.info(f"🔍 [RESET] Причины неудач: все проверенные слоты уже заняты другими пользователями")
            else:
                logging.info(f"🔄 [RESET] Reset-цикл завершен без регистраций для {service_entry.service_name} - нет доступных времен")
            return False
    
    def _get_available_dates_from_date(self, session: requests.Session, 
                                      service_entry: ServiceEntry, slot_length: int,
                                      start_date: str, max_future_days: int = 30) -> List[str]:
        """
        Получает доступные даты начиная с указанной даты (для reset-цикла).
        Игнорирует last_registered_date.
        """
        try:
            url = (f"{self.config.base_url}/branches/{service_entry.branch_id}/dates;"
                  f"servicePublicId={service_entry.service_id};"
                  f"customSlotLength={slot_length}")
            
            dates = session.get(url, timeout=30).json()
            
            # 🔑 ИСПОЛЬЗУЕМ СПЕЦИАЛЬНУЮ ФУНКЦИЮ ДЛЯ RESET-ЦИКЛА
            filtered_dates = find_dates_from_date(dates, start_date, max_future_days)
            
            logging.debug(f"🔄 [RESET] API вернул {len(dates)} дат, отфильтровано {len(filtered_dates)} с {start_date}")
            return filtered_dates
            
        except Exception as e:
            logging.error(f"Ошибка получения дат для reset-цикла {service_entry.service_name}: {e}")
            return []
    
    async def run_reset_cycle_for_all_services(self) -> None:
        """Запускает reset-цикл для всех услуг во всех каналах."""
        if not self.config.reset_cycle_enabled:
            logging.debug("🔄 Reset-цикл отключен в настройках")
            return
        
        start_date = get_server_current_date()
        max_future_days = self.config.reset_cycle_max_future_days
        
        logging.info(f"🔄 Запуск RESET-ЦИКЛА: поиск с {start_date}, максимум {max_future_days} дней вперед")
        
        total_services = 0
        successful_services = 0
        
        for channel in self.config.channels:
            channel_id = channel['id']
            channel_name = channel['name']
            chat_id = channel['chat_id']
            
            logging.info(f"🔄 [RESET] Обработка канала: {channel_name}")
            
            for service_data in channel.get('services', []):
                total_services += 1
                try:
                    service_entry = ServiceEntry(
                        branch_name=service_data['branch_name'],
                        branch_id=service_data['branch_id'],
                        service_name=service_data['service_name'],
                        service_id=service_data['service_id'],
                        qp_id=service_data['qpId'],
                        adult=service_data['adult'],
                        visits_per_day=service_data['visits_per_day'],
                        last_registered_date=None  # 🔑 ИГНОРИРУЕМ last_registered_date!
                    )
                    
                    # 🔑 НЕ ОБНОВЛЯЕМ last_registered_date в конфиге!
                    success = await self.register_visit_from_date(
                        service_entry, channel_id, channel_name, chat_id,
                        start_date, max_future_days
                    )
                    
                    if success:
                        successful_services += 1
                    
                except Exception as e:
                    error_msg = f"Ошибка reset-цикла для услуги {service_data.get('service_name', 'Unknown')}: {e}"
                    logging.error(error_msg)
                    
                    if self.config.telegram_enabled:
                        await self.telegram.send_error_notification(error_msg, chat_id)
        
        logging.info(f"🔄 RESET-ЦИКЛ завершен: {successful_services}/{total_services} услуг с новыми визитами")
        
        # Обновляем сессию для следующего цикла
        self._session = None
    
    def __del__(self):
        """Закрываем сессию при удалении объекта."""
        if self._session:
            self._session.close() 