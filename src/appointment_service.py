"""
Сервис регистрации визитов.
Основная бизнес-логика для автоматической регистрации визитов в системе UM Poznan.
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
from .utils import generate_phone, find_next_dates, get_chrome_session, setup_csrf_token


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
    """Сервис для регистрации визитов в UM Poznan."""
    
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
            return find_next_dates(dates, service_entry.last_registered_date)
            
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
                logging.warning(f"Не удалось зарезервировать {time_slot}")
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
        
        # Пробуем зарегистрироваться на ближайшие даты
        for date in available_dates:
            times = self._get_available_times(self._session, service_entry, date, slot_length)
            if not times:
                continue
            
            successful_registrations = 0
            times_copy = times[:]
            
            while successful_registrations < service_entry.visits_per_day and times_copy:
                time_data = random.choice(times_copy)
                times_copy.remove(time_data)
                time_slot = time_data["time"]
                
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
                else:
                    logging.warning(f"Ошибка подтверждения записи для {time_slot}")
                
                # Задержка между попытками
                time.sleep(random.uniform(5, 10))
            
            # Если есть успешные регистрации, обновляем последнюю дату
            if successful_registrations > 0:
                self.config.update_service_last_date(channel_id, service_entry.service_id, date)
                return True
        
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
    
    def __del__(self):
        """Закрываем сессию при удалении объекта."""
        if self._session:
            self._session.close() 