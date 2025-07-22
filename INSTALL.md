# 🚀 Подробная инструкция по установке Appointment Bot

## 📋 Требования

### Системные требования
- **ОС**: Ubuntu 18.04+ (рекомендуется 20.04+)
- **Архитектура**: x64 (amd64)
- **RAM**: минимум 1GB (рекомендуется 2GB+)
- **Диск**: минимум 2GB свободного места
- **Сеть**: стабильное интернет-соединение

### Необходимые права
- Доступ `sudo` (root права)
- Доступ к интернету для скачивания зависимостей

---

## 🔥 Метод 1: Автоматическая установка одной командой (РЕКОМЕНДУЕТСЯ)

### Установка

```bash
# Скачайте и запустите скрипт установки
wget https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/install.sh && chmod +x install.sh && sudo ./install.sh
```

**Альтернативно с curl:**
```bash
curl -L https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/install.sh -o install.sh && chmod +x install.sh && sudo ./install.sh
```

### Что происходит во время установки

1. **Проверка системы** - проверяется Ubuntu и права sudo
2. **Обновление системы** - `apt update && apt upgrade`
3. **Установка базовых пакетов** - curl, wget, git и др.
4. **Установка Python 3.11** - добавляется PPA и устанавливается Python
5. **Установка Google Chrome** - стабильная версия
6. **Установка ChromeDriver** - автоматически подбирается совместимая версия
7. **Установка Xvfb** - для headless режима браузера
8. **Создание пользователя** - создается `appointment-bot`
9. **Скачивание проекта** - клонируется с GitHub
10. **Настройка Python** - создается venv, устанавливаются зависимости
11. **Создание служб** - systemd службы для автозапуска
12. **Настройка логирования** - logrotate, директории логов
13. **Создание скриптов управления** - удобные команды

### Время установки
- Обычно: 5-10 минут
- На медленных серверах: до 15 минут

---

## ⚙️ Метод 2: Ручная установка (для опытных пользователей)

### Шаг 1: Подготовка системы

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых пакетов
sudo apt install -y curl wget git software-properties-common apt-transport-https ca-certificates gnupg lsb-release
```

### Шаг 2: Установка Python 3.11

```bash
# Добавление PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Установка Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
```

### Шаг 3: Установка Google Chrome

```bash
# Добавление ключа и репозитория
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

# Установка Chrome
sudo apt update
sudo apt install -y google-chrome-stable
```

### Шаг 4: Установка ChromeDriver

```bash
# Определение версии Chrome
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION%%.*}")

# Скачивание и установка ChromeDriver
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
sudo unzip /tmp/chromedriver.zip -d /tmp/
sudo mv /tmp/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
rm /tmp/chromedriver.zip
```

### Шаг 5: Установка Xvfb

```bash
sudo apt install -y xvfb
```

### Шаг 6: Создание пользователя

```bash
sudo useradd -m -s /bin/bash appointment-bot
sudo usermod -aG sudo appointment-bot
```

### Шаг 7: Установка проекта

```bash
# Переход в домашнюю директорию пользователя
sudo su - appointment-bot
cd ~

# Клонирование проекта
git clone https://github.com/Poleno7682/appointment-bot.git
cd appointment-bot

# Создание виртуального окружения
python3.11 -m venv venv

# Активация и установка зависимостей
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Выход из сессии пользователя
exit
```

### Шаг 8: Создание systemd служб

**Создание службы Xvfb:**
```bash
sudo tee /etc/systemd/system/xvfb.service << 'EOF'
[Unit]
Description=X Virtual Framebuffer
After=network.target

[Service]
Type=simple
User=appointment-bot
Group=appointment-bot
ExecStart=/usr/bin/Xvfb :99 -screen 0 1024x768x24
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

**Создание службы бота:**
```bash
sudo tee /etc/systemd/system/appointment-bot.service << 'EOF'
[Unit]
Description=Appointment Bot for UM Poznan
After=network.target xvfb.service
Requires=xvfb.service

[Service]
Type=simple
User=appointment-bot
Group=appointment-bot
WorkingDirectory=/home/appointment-bot/appointment-bot
ExecStart=/home/appointment-bot/appointment-bot/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=DISPLAY=:99
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### Шаг 9: Активация служб

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable xvfb
sudo systemctl enable appointment-bot
```

---

## 🔧 Настройка после установки

### 1. Настройка Telegram Bot

```bash
# Отредактируйте конфигурацию каналов
sudo nano /home/appointment-bot/appointment-bot/config/channels.json
```

**Обновите следующие параметры:**
- `bot_token` - токен вашего Telegram бота
- `chat_id` - ID чатов для уведомлений
- Настройте services для каждого канала

### 2. Настройка основных параметров

```bash
# Отредактируйте основные настройки
sudo nano /home/appointment-bot/appointment-bot/config/settings.json
```

**При необходимости измените:**
- `email` - ваш email для регистрации
- `repeat_minutes` - интервал проверки (по умолчанию 30 минут)
- Другие параметры согласно вашим требованиям

### 3. Запуск бота

```bash
# Запуск всех служб
sudo systemctl start xvfb
sudo systemctl start appointment-bot

# Проверка статуса
sudo systemctl status appointment-bot
```

---

## 📊 Управление ботом

### Основные команды

```bash
# Запуск
sudo appointment-bot-ctl start

# Остановка
sudo appointment-bot-ctl stop

# Перезапуск
sudo appointment-bot-ctl restart

# Статус
sudo appointment-bot-ctl status

# Логи в реальном времени
sudo appointment-bot-ctl logs

# Включение автозапуска
sudo appointment-bot-ctl enable

# Отключение автозапуска
sudo appointment-bot-ctl disable

# Обновление с GitHub
sudo appointment-bot-ctl update
```

### Системные команды

```bash
# Статус служб
sudo systemctl status appointment-bot
sudo systemctl status xvfb

# Логи
sudo journalctl -u appointment-bot -f
sudo journalctl -u xvfb -f

# Перезапуск служб
sudo systemctl restart appointment-bot
sudo systemctl restart xvfb
```

---

## 📝 Логирование

### Расположение логов

- **Системные логи**: `sudo journalctl -u appointment-bot`
- **Логи приложения**: `/home/appointment-bot/appointment-bot/appointment_bot.log`
- **Директория логов**: `/var/log/appointment-bot/`

### Просмотр логов

```bash
# Последние 50 записей
sudo journalctl -u appointment-bot -n 50

# Логи в реальном времени
sudo journalctl -u appointment-bot -f

# Логи за сегодня
sudo journalctl -u appointment-bot --since today

# Логи с ошибками
sudo journalctl -u appointment-bot -p err
```

---

## 🔄 Обновление

### Автоматическое обновление

```bash
sudo appointment-bot-ctl update
```

### Ручное обновление

```bash
cd /home/appointment-bot/appointment-bot
sudo -u appointment-bot git pull origin main
sudo -u appointment-bot ./venv/bin/pip install -r requirements.txt
sudo systemctl restart appointment-bot
```

---

## 🛠️ Устранение неполадок

### Проблема: Бот не запускается

**Решение:**
```bash
# Проверьте статус
sudo systemctl status appointment-bot

# Проверьте логи
sudo journalctl -u appointment-bot -n 20

# Проверьте конфигурацию
sudo nano /home/appointment-bot/appointment-bot/config/channels.json
```

### Проблема: Ошибки Chrome/ChromeDriver

**Решение:**
```bash
# Проверьте Xvfb
sudo systemctl status xvfb

# Переустановите Chrome
sudo apt-get remove google-chrome-stable
sudo apt-get install google-chrome-stable

# Проверьте ChromeDriver
chromedriver --version
google-chrome --version
```

### Проблема: Ошибки Telegram

**Проверьте:**
1. Корректность `bot_token`
2. Правильность `chat_id`
3. Добавлен ли бот в каналы
4. Имеет ли бот права администратора

### Проблема: Высокое потребление ресурсов

**Решение:**
```bash
# Проверьте процессы
ps aux | grep appointment
ps aux | grep chrome

# Проверьте память
free -h

# Перезапустите службы
sudo systemctl restart appointment-bot
sudo systemctl restart xvfb
```

---

## 🔐 Безопасность

### Рекомендации по безопасности

1. **Ограничьте доступ к конфигурации:**
   ```bash
   sudo chmod 600 /home/appointment-bot/appointment-bot/config/*.json
   ```

2. **Регулярно обновляйте систему:**
   ```bash
   sudo apt update && sudo apt upgrade
   ```

3. **Мониторьте логи на подозрительную активность**

4. **Используйте firewall:**
   ```bash
   sudo ufw enable
   sudo ufw allow ssh
   ```

### Резервное копирование

```bash
# Создание backup конфигурации
sudo cp -r /home/appointment-bot/appointment-bot/config /backup/appointment-bot-config-$(date +%Y%m%d)

# Восстановление из backup
sudo cp -r /backup/appointment-bot-config-YYYYMMDD/* /home/appointment-bot/appointment-bot/config/
sudo systemctl restart appointment-bot
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `sudo appointment-bot-ctl logs`
2. Проверьте статус: `sudo appointment-bot-ctl status`  
3. Изучите документацию: [GitHub Repository](https://github.com/Poleno7682/appointment-bot)
4. Проверьте системные требования
5. Убедитесь в корректности конфигурации

---

**✅ После успешной установки бот готов к работе!** 