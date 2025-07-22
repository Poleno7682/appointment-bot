# Appointment Bot

Автоматическая система регистрации визитов в Urząd Miasta Poznań с уведомлениями в Telegram.

## Особенности

- ✅ Автоматическая регистрация визитов в UM Poznan
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

## Быстрая установка

### 1. Клонирование репозитория

```bash
# Клонируйте проект с GitHub
git clone https://github.com/YOUR_USERNAME/appointment-bot.git
cd appointment-bot

# Или скачайте ZIP архив и распакуйте
wget https://github.com/YOUR_USERNAME/appointment-bot/archive/main.zip
unzip main.zip
cd appointment-bot-main
```

### 2. Развертывание

```bash
# Сделайте скрипт исполняемым
chmod +x deploy.sh

# Запустите установку (требуются права root)
sudo ./deploy.sh
```

Скрипт автоматически:
- Обновит систему
- Установит все зависимости (Chrome, ChromeDriver, Python пакеты)
- Создаст пользователя сервиса
- Настроит systemd сервис
- Добавит сервис в автозагрузку

### 3. Настройка

#### Настройка Telegram

Отредактируйте файл каналов:
```bash
nano /opt/appointment_bot/config/channels.json
```

Замените `bot_token` на ваш токен и настройте `chat_id` для каналов.

#### Настройка email

Email настраивается автоматически во время установки, но можно изменить в:
```bash
nano /opt/appointment_bot/config/settings.json
```

## Управление сервисом

После установки доступна команда `appointment_bot-ctl`:

```bash
# Запуск сервиса
appointment_bot-ctl start

# Остановка сервиса
appointment_bot-ctl stop

# Перезапуск сервиса
appointment_bot-ctl restart

# Статус сервиса
appointment_bot-ctl status

# Просмотр логов
appointment_bot-ctl logs

# Просмотр ошибок
appointment_bot-ctl errors

# Редактирование конфигурации
appointment_bot-ctl config
```

## Конфигурация

### settings.json

Основные настройки приложения:

```json
{
  "base_url": "https://rezerwacja5.um.poznan.pl/qmaticwebbooking/rest/schedule",
  "site_url": "https://rezerwacja5.um.poznan.pl/qmaticwebbooking/",
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
          "branch_name": "DĘBIEC",
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
- `/var/log/appointment_bot/service.log` - основные логи
- `/var/log/appointment_bot/error.log` - ошибки
- `/opt/appointment_bot/appointment_bot.log` - детальные логи приложения

## Мониторинг

### Статус сервиса
```bash
systemctl status appointment_bot
```

### Автозагрузка
```bash
systemctl is-enabled appointment_bot
```

### Системные ресурсы
```bash
journalctl -u appointment_bot -f
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
   appointment_bot-ctl logs
   appointment_bot-ctl errors
   ```

2. Проверьте конфигурацию:
   ```bash
   appointment_bot-ctl config
   ```

3. Проверьте системный статус:
   ```bash
   systemctl status appointment_bot
   ```

### Chrome/ChromeDriver ошибки

```bash
# Переустановите Chrome
sudo apt-get remove google-chrome-stable
sudo apt-get install google-chrome-stable

# Проверьте Xvfb
systemctl status xvfb
```

### Telegram ошибки

1. Проверьте токен бота
2. Убедитесь, что бот добавлен в каналы
3. Проверьте chat_id каналов

## Безопасность

- Сервис работает под отдельным пользователем `appointment`
- Ограниченные права доступа к файловой системе
- Изоляция процессов через systemd
- Логирование всех операций

## Лицензия

Проект создан для автоматизации регистрации визитов в UM Poznan.
Используйте ответственно и в соответствии с правилами сервиса. 