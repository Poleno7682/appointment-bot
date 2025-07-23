# 🔧 Настройка конфигурации

После установки бота необходимо настроить конфигурационные файлы.

## 📋 Быстрая настройка

### 1. Скопируйте шаблоны:
```bash
sudo -u appointment-bot cp /home/appointment-bot/appointment-bot/config/settings.json.example /home/appointment-bot/appointment-bot/config/settings.json
sudo -u appointment-bot cp /home/appointment-bot/appointment-bot/config/channels.json.example /home/appointment-bot/appointment-bot/config/channels.json
```

### 2. Отредактируйте файлы:
```bash
sudo nano /home/appointment-bot/appointment-bot/config/settings.json
sudo nano /home/appointment-bot/appointment-bot/config/channels.json
```

## ⚙️ Настройки файлов

### 📄 `settings.json`
- **base_url**: API эндпоинт системы бронирования
- **site_url**: URL веб-сайта для получения сессии
- **email**: Email для регистрации визитов
- **repeat_minutes**: Интервал проверки (в минутах)
- **prefixes**: Префиксы номеров телефонов для генерации

### 📢 `channels.json`
- **bot_token**: Токен Telegram бота
- **channels**: Массив каналов, каждый со своими услугами
  - **chat_id**: ID Telegram чата для уведомлений
  - **services**: Услуги для этого канала
    - **branch_id/service_id**: ID ветки и услуги из API
    - **adult**: Количество взрослых
    - **visits_per_day**: Максимум визитов в день

## 🔍 Как получить ID?

### Telegram Chat ID:
1. Добавьте бота @userinfobot в свой канал
2. Отправьте `/start`
3. Используйте отрицательный ID для каналов: `-1002567348249`

### Branch/Service ID:
1. Откройте Developer Tools в браузере
2. Перейдите на сайт бронирования  
3. Найдите API запросы с нужными ID

## 🚀 Запуск после настройки:
```bash
sudo appointment-bot-ctl start
sudo appointment-bot-ctl logs
``` 