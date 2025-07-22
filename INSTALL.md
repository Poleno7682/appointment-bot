# Установка Appointment Bot с GitHub на Ubuntu Server

Пошаговая инструкция по развертыванию проекта с GitHub репозитория на Ubuntu сервер.

## 📋 Предварительные требования

- Ubuntu 20.04+ или Debian 11+
- Доступ к серверу по SSH (root или sudo права)
- Активное интернет соединение

## 🚀 Автоматическая установка (Рекомендуется)

### Шаг 1: Подключение к серверу и клонирование

```bash
# Подключитесь к серверу
ssh user@your-server-ip

# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите git если не установлен
sudo apt install git -y

# Клонируйте проект
git clone https://github.com/YOUR_USERNAME/appointment-bot.git
cd appointment-bot
```

### Шаг 2: Запуск автоматической установки

```bash
# Сделайте скрипт исполняемым
chmod +x deploy.sh

# Запустите установку
sudo ./deploy.sh
```

**Скрипт автоматически:**
- Установит все системные зависимости
- Создаст пользователя сервиса `appointment`
- Настроит Python окружение
- Установит Chrome и ChromeDriver
- Создаст systemd сервис
- Настроит автозагрузку

### Шаг 3: Настройка конфигурации

```bash
# Настройте Telegram токены
appointment_bot-ctl config

# Или вручную отредактируйте файл
sudo nano /opt/appointment_bot/config/channels.json
```

### Шаг 4: Запуск сервиса

```bash
# Запустите сервис
appointment_bot-ctl start

# Проверьте статус
appointment_bot-ctl status

# Посмотрите логи
appointment_bot-ctl logs
```

## 🛠️ Ручная установка

### Шаг 1: Подготовка системы

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install -y python3 python3-pip python3-venv git curl wget unzip

# Установка Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# Установка ChromeDriver
sudo apt install -y chromium-chromedriver

# Установка Xvfb для headless режима
sudo apt install -y xvfb
```

### Шаг 2: Создание пользователя и директорий

```bash
# Создание системного пользователя
sudo useradd --system --home-dir /opt/appointment_bot --shell /bin/false appointment

# Создание директорий
sudo mkdir -p /opt/appointment_bot
sudo mkdir -p /var/log/appointment_bot

# Клонирование проекта
sudo git clone https://github.com/YOUR_USERNAME/appointment-bot.git /opt/appointment_bot

# Установка прав
sudo chown -R appointment:appointment /opt/appointment_bot
sudo chown -R appointment:appointment /var/log/appointment_bot
```

### Шаг 3: Настройка Python окружения

```bash
cd /opt/appointment_bot

# Создание виртуального окружения
sudo -u appointment python3 -m venv venv

# Активация и установка зависимостей
sudo -u appointment bash -c "source venv/bin/activate && pip install --upgrade pip"
sudo -u appointment bash -c "source venv/bin/activate && pip install -r requirements.txt"
```

### Шаг 4: Настройка конфигурации

```bash
# Настройка email
sudo nano /opt/appointment_bot/config/settings.json

# Настройка Telegram каналов
sudo nano /opt/appointment_bot/config/channels.json
```

### Шаг 5: Создание systemd сервиса

```bash
# Создание сервисного файла
sudo tee /etc/systemd/system/appointment_bot.service << 'EOF'
[Unit]
Description=Appointment Bot - UM Poznan Registration Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=appointment
Group=appointment
WorkingDirectory=/opt/appointment_bot
ExecStart=/opt/appointment_bot/venv/bin/python /opt/appointment_bot/main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/appointment_bot/service.log
StandardError=append:/var/log/appointment_bot/error.log

# Environment variables
Environment=PYTHONPATH=/opt/appointment_bot
Environment=DISPLAY=:99

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/appointment_bot /var/log/appointment_bot

# Resource limits
LimitNOFILE=65536
MemoryLimit=512M

[Install]
WantedBy=multi-user.target
EOF

# Настройка Xvfb
sudo tee /etc/systemd/system/xvfb.service << 'EOF'
[Unit]
Description=Virtual Framebuffer X Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/Xvfb :99 -screen 0 1024x768x24
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd и включение сервисов
sudo systemctl daemon-reload
sudo systemctl enable appointment_bot
sudo systemctl enable xvfb
sudo systemctl start xvfb
```

### Шаг 6: Создание команд управления

```bash
# Создание команды управления
sudo tee /usr/local/bin/appointment_bot-ctl << 'EOF'
#!/bin/bash

SERVICE_NAME="appointment_bot"
LOG_DIR="/var/log/appointment_bot"

case "$1" in
    start)
        systemctl start $SERVICE_NAME
        echo "Сервис запущен"
        ;;
    stop)
        systemctl stop $SERVICE_NAME
        echo "Сервис остановлен"
        ;;
    restart)
        systemctl restart $SERVICE_NAME
        echo "Сервис перезапущен"
        ;;
    status)
        systemctl status $SERVICE_NAME
        ;;
    logs)
        tail -f $LOG_DIR/service.log
        ;;
    errors)
        tail -f $LOG_DIR/error.log
        ;;
    config)
        nano /opt/appointment_bot/config/channels.json
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|errors|config}"
        exit 1
        ;;
esac
EOF

sudo chmod +x /usr/local/bin/appointment_bot-ctl
```

## ⚙️ Настройка конфигурации

### Основные настройки (settings.json)

```json
{
  "email": "your-email@example.com",
  "repeat_minutes": 30,
  "prefixes": ["733", "668", "883", ...],
  "logging": {
    "level": "INFO",
    "file": "appointment_bot.log"
  }
}
```

### Telegram каналы (channels.json)

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
      "chat_id": "CHAT_ID",
      "services": [...]
    }
  ]
}
```

## 🎯 Запуск и управление

```bash
# Запуск сервиса
appointment_bot-ctl start

# Проверка статуса
appointment_bot-ctl status

# Просмотр логов
appointment_bot-ctl logs

# Просмотр ошибок
appointment_bot-ctl errors

# Остановка сервиса
appointment_bot-ctl stop

# Перезапуск сервиса
appointment_bot-ctl restart

# Редактирование конфигурации
appointment_bot-ctl config
```

## 📊 Мониторинг

### Проверка системных сервисов

```bash
# Статус основного сервиса
sudo systemctl status appointment_bot

# Статус Xvfb
sudo systemctl status xvfb

# Логи через journalctl
sudo journalctl -u appointment_bot -f

# Проверка процессов
ps aux | grep appointment
```

### Мониторинг ресурсов

```bash
# Использование памяти
sudo systemctl show appointment_bot --property=MemoryCurrent

# Статистика сервиса
sudo systemctl show appointment_bot

# Логи за последний час
sudo journalctl -u appointment_bot --since "1 hour ago"
```

## 🔧 Обновление проекта

```bash
# Остановка сервиса
appointment_bot-ctl stop

# Переход в директорию проекта
cd /opt/appointment_bot

# Обновление кода
sudo -u appointment git pull origin main

# Обновление зависимостей (если нужно)
sudo -u appointment bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Перезапуск сервиса
appointment_bot-ctl start
```

## 🛡️ Безопасность

### Настройка firewall

```bash
# Установка UFW
sudo apt install ufw

# Базовые правила
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable
```

### Настройка автоматических обновлений

```bash
# Установка unattended-upgrades
sudo apt install unattended-upgrades

# Конфигурация
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 🚨 Устранение неполадок

### Проблемы с Chrome/ChromeDriver

```bash
# Переустановка Chrome
sudo apt-get remove google-chrome-stable
sudo apt-get install google-chrome-stable

# Проверка ChromeDriver
which chromedriver
chromedriver --version

# Проверка Xvfb
sudo systemctl status xvfb
```

### Проблемы с правами

```bash
# Восстановление прав
sudo chown -R appointment:appointment /opt/appointment_bot
sudo chown -R appointment:appointment /var/log/appointment_bot
```

### Проблемы с Python зависимостями

```bash
# Переустановка окружения
cd /opt/appointment_bot
sudo -u appointment rm -rf venv
sudo -u appointment python3 -m venv venv
sudo -u appointment bash -c "source venv/bin/activate && pip install -r requirements.txt"
```

## 📞 Получение помощи

При возникновении проблем:

1. Проверьте логи: `appointment_bot-ctl logs`
2. Проверьте статус: `appointment_bot-ctl status`
3. Проверьте конфигурацию: `appointment_bot-ctl config`
4. Перезапустите сервис: `appointment_bot-ctl restart`

Для диагностики создайте issue в GitHub репозитории с приложением логов и описанием проблемы. 