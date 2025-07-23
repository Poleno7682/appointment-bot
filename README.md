# 🤖 Appointment Bot

Автоматический бот для регистрации визитов в системах онлайн-записи с отправкой уведомлений в Telegram.

## ✨ Возможности

- 🔄 **Автоматическая регистрация визитов** в системе онлайн-записи
- 📱 **Telegram уведомления** о успешных регистрациях  
- 🎯 **Мульти-канальная поддержка** - разные услуги в разные каналы
- ⚙️ **Гибкие настройки** лимитов визитов и интервалов проверки
- 🔁 **Reset-цикл** - периодический поиск освободившихся мест
- 🛡️ **Надежность** - автоматические повторы при ошибках
- 📊 **Детальное логирование** всех операций
- 🔐 **Безопасность** - работа с CSRF токенами и сессиями

## Особенности

- ✅ Автоматическая регистрация визитов в системе онлайн-записи
- ✅ Поддержка множественных Telegram каналов
- ✅ Обработка callback'ов от Telegram Bot API
- ✅ Генерация случайных номеров телефонов
- ✅ Система повторных попыток при ошибках
- ✅ Подробное логирование
- ✅ Systemd интеграция для автозагрузки
- ✅ Модульная архитектура (SOLID принципы)

## Структура проекта

```
appointment_bot/
├── main.py                  # Точка входа приложения
├── config/
│   ├── settings.json        # Основные настройки
│   └── channels.json        # Конфигурация Telegram каналов
├── src/
│   ├── __init__.py
│   ├── config_manager.py    # Управление конфигурацией
│   ├── appointment_service.py # Сервис регистрации визитов
│   ├── telegram_service.py  # Telegram Bot API
│   └── utils.py            # Утилиты
├── requirements.txt         # Python зависимости
├── deploy.sh               # Скрипт развертывания
└── README.md               # Документация
```

## Системные требования

- **ОС**: Ubuntu 20.04+ или Debian 11+
- **Python**: 3.8+
- **RAM**: 512MB минимум
- **Диск**: 500MB свободного места
- **Сеть**: Доступ к интернету

## 🚀 Быстрая установка

### Автоматическая установка одной командой

```bash
# Установка одной командой (Ubuntu)
wget https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/install.sh && chmod +x install.sh && sudo ./install.sh
```

**Альтернативные способы:**
```bash
# Если wget недоступен
curl -L https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/install.sh -o install.sh && chmod +x install.sh && sudo ./install.sh

# Или скачайте и запустите вручную
wget https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

**🔥 Что делает скрипт автоматически:**
- ✅ Проверяет совместимость с Ubuntu
- ✅ Обновляет систему
- ✅ Устанавливает Python 3.11, Chrome, ChromeDriver
- ✅ Скачивает проект с GitHub
- ✅ Создает пользователя `appointment-bot`
- ✅ Настраивает виртуальное окружение
- ✅ Устанавливает Python зависимости
- ✅ Создает systemd службы (appointment-bot, xvfb)
- ✅ Настраивает автозапуск
- ✅ Создает удобный скрипт управления
- ✅ Настраивает логирование

### 3. Настройка

#### Настройка Telegram

Отредактируйте файл каналов:
```bash
sudo nano /home/appointment-bot/appointment-bot/config/channels.json
```

Замените `bot_token` на ваш токен и настройте `chat_id` для каналов.

#### Настройка email

Email можно изменить в основных настройках:
```bash
sudo nano /home/appointment-bot/appointment-bot/config/settings.json
```

## Управление сервисом

После установки доступна команда `appointment-bot-ctl`:

```bash
# Запуск сервиса
sudo appointment-bot-ctl start

# Остановка сервиса  
sudo appointment-bot-ctl stop

# Перезапуск сервиса
sudo appointment-bot-ctl restart

# Статус сервиса
sudo appointment-bot-ctl status

# Просмотр логов
sudo appointment-bot-ctl logs

# Включение автозапуска
sudo appointment-bot-ctl enable

# Отключение автозапуска
sudo appointment-bot-ctl disable

# Обновление проекта с GitHub
sudo appointment-bot-ctl update

# 🚀 ПОЛНОЕ обновление сервера (все компоненты)
wget https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/update-server.sh && chmod +x update-server.sh && sudo ./update-server.sh
```

## Конфигурация

### settings.json

Основные настройки приложения:

```json
{
  "base_url": "https://your-booking-system.com/api/schedule",
  "site_url": "https://your-booking-system.com/booking/",
  "email": "your-email@example.com",
  "repeat_minutes": 30,
  "prefixes": ["733", "668", "883", ...],
  "retry_settings": {
    "max_retries": 5,
    "initial_delay": 1,
    "delay_multiplier": 2
  },
  "logging": {
    "level": "INFO",
    "file": "appointment_bot.log",
    "format": "[%(asctime)s] [%(levelname)s] %(message)s"
  }
}
```

### channels.json

Конфигурация Telegram каналов и услуг:

```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "enabled": true
  },
  "channels": [
    {
      "id": "channel_1",
      "name": "Channel Name",
      "chat_id": "-1001234567890",
      "services": [
        {
          "branch_name": "YOUR_BRANCH_NAME",
          "branch_id": "branch_hash",
          "service_name": "Service Name",
          "service_id": "service_hash",
          "qpId": "55",
          "adult": 3,
          "visits_per_day": 2,
          "last_registered_date": null
        }
      ]
    }
  ]
}
```

## Логирование

Логи сохраняются в:
- `journalctl -u appointment-bot` - системные логи службы
- `/var/log/appointment-bot/` - директория логов приложения  
- `/home/appointment-bot/appointment-bot/appointment_bot.log` - детальные логи приложения

## Мониторинг

### Статус сервиса
```bash
sudo systemctl status appointment-bot
```

### Автозагрузка
```bash
sudo systemctl is-enabled appointment-bot
```

### Системные ресурсы
```bash
sudo journalctl -u appointment-bot -f
```

## Архитектура

Проект следует принципам SOLID:

- **S** - Single Responsibility: каждый модуль отвечает за одну задачу
- **O** - Open/Closed: легко расширяется без изменения существующего кода
- **L** - Liskov Substitution: компоненты взаимозаменяемы
- **I** - Interface Segregation: четкие интерфейсы между модулями
- **D** - Dependency Inversion: зависимости инвертированы через DI

### Компоненты

1. **ConfigManager** - управление конфигурацией (Singleton)
2. **TelegramService** - работа с Telegram API
3. **AppointmentService** - бизнес-логика регистрации
4. **Utils** - вспомогательные функции

## Устранение неполадок

### Сервис не запускается

1. Проверьте логи:
   ```bash
   sudo appointment-bot-ctl logs
   sudo journalctl -u appointment-bot -n 50
   ```

2. Проверьте конфигурацию:
   ```bash
   sudo nano /home/appointment-bot/appointment-bot/config/channels.json
   sudo nano /home/appointment-bot/appointment-bot/config/settings.json
   ```

3. Проверьте системный статус:
   ```bash
   sudo systemctl status appointment-bot
   sudo systemctl status xvfb
   ```

### Chrome/ChromeDriver ошибки

```bash
# Переустановите Chrome
sudo apt-get remove google-chrome-stable
sudo apt-get install google-chrome-stable

# Проверьте Xvfb
sudo systemctl status xvfb
```

### Telegram ошибки

1. Проверьте токен бота
2. Убедитесь, что бот добавлен в каналы
3. Проверьте chat_id каналов

## Безопасность

- Сервис работает под отдельным пользователем `appointment-bot`
- Ограниченные права доступа к файловой системе
- Изоляция процессов через systemd
- Логирование всех операций

## Лицензия

Проект создан для автоматизации регистрации визитов в системах онлайн-записи.
Используйте ответственно и в соответствии с правилами сервиса. 
