#!/bin/bash

# 🤖 Appointment Bot - Автоматическая установка одной командой
# Использование: wget https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/install.sh && chmod +x install.sh && sudo ./install.sh

set -e

# Глобальные переменные
PYTHON_CMD="python3.11"  # По умолчанию

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция логирования
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Проверка root прав
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Запустите скрипт с правами sudo: sudo ./install.sh"
    fi
}

# Проверка Ubuntu
check_ubuntu() {
    if [ ! -f /etc/os-release ]; then
        error "Не удается определить операционную систему"
    fi
    
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        error "Этот скрипт предназначен только для Ubuntu"
    fi
    
    log "Обнаружена Ubuntu $VERSION_ID"
}

# Установка базовых зависимостей
install_dependencies() {
    log "Обновление системы..."
    apt update && apt upgrade -y
    
    log "Установка базовых пакетов..."
    apt install -y curl wget git software-properties-common apt-transport-https ca-certificates gnupg lsb-release unzip
    
    # Определяем версию Ubuntu
    . /etc/os-release
    UBUNTU_VERSION_NUM=$(echo $VERSION_ID | cut -d'.' -f1)
    
    # Python 3.11 - проверяем поддержку PPA для версии Ubuntu
    log "Проверка поддержки Python 3.11..."
    
    # Список поддерживаемых версий Ubuntu для deadsnakes PPA
    SUPPORTED_UBUNTU_VERSIONS="20 22 24"
    
    if echo "$SUPPORTED_UBUNTU_VERSIONS" | grep -q "$UBUNTU_VERSION_NUM"; then
        log "Добавление репозитория Python 3.11..."
        add-apt-repository ppa:deadsnakes/ppa -y
        apt update
        
        log "Установка Python 3.11 из PPA..."
        apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
        PYTHON_CMD="python3.11"
    else
        warn "Ubuntu $VERSION_ID не поддерживается в deadsnakes PPA"
        
        # Удаляем проблемный PPA если он был добавлен ранее
        if [ -f /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-plucky.sources ]; then
            log "Удаление несовместимого PPA deadsnakes..."
            rm -f /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-plucky.sources
            apt update
        fi
        
        log "Проверка системного Python..."
        
        # Проверяем доступные версии Python в системе
        if command -v python3.12 &> /dev/null; then
            log "Используем системный Python 3.12"
            apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
            PYTHON_CMD="python3.12"
        elif command -v python3.11 &> /dev/null; then
            log "Используем системный Python 3.11"
            apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
            PYTHON_CMD="python3.11"
        elif command -v python3.10 &> /dev/null; then
            log "Используем системный Python 3.10"
            apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
            PYTHON_CMD="python3.10"
        elif command -v python3.9 &> /dev/null; then
            log "Используем системный Python 3.9"
            apt install -y python3.9 python3.9-venv python3.9-dev python3-pip
            PYTHON_CMD="python3.9"
        elif command -v python3.8 &> /dev/null; then
            log "Используем системный Python 3.8"
            apt install -y python3.8 python3.8-venv python3.8-dev python3-pip
            PYTHON_CMD="python3.8"
        elif command -v python3 &> /dev/null; then
            PYTHON_VERSION=$(python3 --version | awk '{print $2}')
            log "Используем системный Python $PYTHON_VERSION"
            apt install -y python3 python3-venv python3-dev python3-pip
            PYTHON_CMD="python3"
        else
            error "Python 3.8+ не найден в системе"
        fi
    fi
    
    log "Используемая версия Python: $($PYTHON_CMD --version)"
    
    # Google Chrome
    log "Установка Google Chrome..."
    if ! command -v google-chrome &> /dev/null; then
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
        apt update
        apt install -y google-chrome-stable
    else
        log "Google Chrome уже установлен"
    fi
    
    # ChromeDriver
    log "Установка ChromeDriver..."
    CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION%%.*}")
    
    wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
    unzip /tmp/chromedriver.zip -d /tmp/
    mv /tmp/chromedriver /usr/local/bin/
    chmod +x /usr/local/bin/chromedriver
    rm /tmp/chromedriver.zip
    
    # Xvfb для headless режима
    log "Установка Xvfb..."
    apt install -y xvfb
}

# Создание пользователя
create_user() {
    log "Создание пользователя appointment-bot..."
    
    if id "appointment-bot" &>/dev/null; then
        warn "Пользователь appointment-bot уже существует"
    else
        useradd -m -s /bin/bash appointment-bot
        usermod -aG sudo appointment-bot
        log "Пользователь appointment-bot создан"
    fi
}

# Скачивание и установка проекта
install_project() {
    log "Скачивание проекта с GitHub..."
    
    PROJECT_DIR="/home/appointment-bot"
    
    # Удаляем старую версию если есть
    if [ -d "$PROJECT_DIR/appointment-bot" ]; then
        rm -rf "$PROJECT_DIR/appointment-bot"
    fi
    
    # Клонируем проект
    cd "$PROJECT_DIR"
    sudo -u appointment-bot git clone https://github.com/Poleno7682/appointment-bot.git
    cd appointment-bot
    
    log "Создание виртуального окружения..."
    sudo -u appointment-bot $PYTHON_CMD -m venv venv
    
    log "Установка Python зависимостей..."
    sudo -u appointment-bot ./venv/bin/pip install --upgrade pip
    sudo -u appointment-bot ./venv/bin/pip install -r requirements.txt
    
    # Установка прав
    chown -R appointment-bot:appointment-bot "$PROJECT_DIR"
    chmod +x "$PROJECT_DIR/appointment-bot/main.py"
}

# Создание systemd служб
create_services() {
    log "Создание systemd служб..."
    
    # Xvfb служба
    cat > /etc/systemd/system/xvfb.service << 'EOF'
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

    # Appointment Bot служба
    cat > /etc/systemd/system/appointment-bot.service << 'EOF'
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

    # Перезагрузка systemd
    systemctl daemon-reload
    
    # Включение автозапуска
    systemctl enable xvfb
    systemctl enable appointment-bot
    
    log "Systemd службы созданы и включены в автозапуск"
}

# Создание скрипта управления
create_management_script() {
    log "Создание скрипта управления..."
    
    cat > /usr/local/bin/appointment-bot-ctl << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "Запуск Appointment Bot..."
        systemctl start xvfb
        systemctl start appointment-bot
        ;;
    stop)
        echo "Остановка Appointment Bot..."
        systemctl stop appointment-bot
        systemctl stop xvfb
        ;;
    restart)
        echo "Перезапуск Appointment Bot..."
        systemctl restart appointment-bot
        ;;
    status)
        echo "=== Статус служб ==="
        systemctl status xvfb --no-pager -l
        echo ""
        systemctl status appointment-bot --no-pager -l
        ;;
    logs)
        echo "=== Логи Appointment Bot ==="
        journalctl -u appointment-bot -f
        ;;
    enable)
        echo "Включение автозапуска..."
        systemctl enable xvfb
        systemctl enable appointment-bot
        ;;
    disable)
        echo "Отключение автозапуска..."
        systemctl disable appointment-bot
        systemctl disable xvfb
        ;;
    update)
        echo "Обновление проекта..."
        cd /home/appointment-bot/appointment-bot
        sudo -u appointment-bot git pull origin main
        sudo -u appointment-bot ./venv/bin/pip install -r requirements.txt
        systemctl restart appointment-bot
        echo "Проект обновлен и перезапущен"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|enable|disable|update}"
        echo ""
        echo "Команды:"
        echo "  start    - Запустить бота"
        echo "  stop     - Остановить бота"
        echo "  restart  - Перезапустить бота"
        echo "  status   - Показать статус служб"
        echo "  logs     - Показать логи (Ctrl+C для выхода)"
        echo "  enable   - Включить автозапуск"
        echo "  disable  - Отключить автозапуск"
        echo "  update   - Обновить проект с GitHub"
        exit 1
        ;;
esac
EOF

    chmod +x /usr/local/bin/appointment-bot-ctl
    log "Скрипт управления создан: appointment-bot-ctl"
}

# Создание примера конфигурации
create_sample_config() {
    log "Создание примера конфигурации..."
    
    CONFIG_DIR="/home/appointment-bot/appointment-bot/config"
    
    # Создаем backup оригинальных файлов
    cp "$CONFIG_DIR/settings.json" "$CONFIG_DIR/settings.json.example"
    cp "$CONFIG_DIR/channels.json" "$CONFIG_DIR/channels.json.example"
    
    # Создаем файл с инструкциями
    cat > "$CONFIG_DIR/README_SETUP.txt" << 'EOF'
🔧 НАСТРОЙКА КОНФИГУРАЦИИ

1. Отредактируйте файл channels.json:
   sudo nano /home/appointment-bot/appointment-bot/config/channels.json
   
   Обновите:
   - bot_token: токен вашего Telegram бота
   - chat_id: ID чатов для уведомлений
   - service_id и branch_id: актуальные ID услуг

2. Отредактируйте файл settings.json (при необходимости):
   sudo nano /home/appointment-bot/appointment-bot/config/settings.json

3. После настройки запустите бота:
   sudo appointment-bot-ctl start

4. Проверьте статус:
   sudo appointment-bot-ctl status

5. Просмотр логов:
   sudo appointment-bot-ctl logs
EOF

    chown -R appointment-bot:appointment-bot "$CONFIG_DIR"
    log "Примеры конфигурации созданы в $CONFIG_DIR"
}

# Финальная настройка
final_setup() {
    log "Финальная настройка..."
    
    # Создание директории для логов
    mkdir -p /var/log/appointment-bot
    chown appointment-bot:appointment-bot /var/log/appointment-bot
    
    # Настройка logrotate
    cat > /etc/logrotate.d/appointment-bot << 'EOF'
/var/log/appointment-bot/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        systemctl reload appointment-bot
    endscript
}
EOF

    log "Настройка завершена"
}

# Основная функция
main() {
    echo "🤖 Appointment Bot - Автоматическая установка"
    echo "============================================="
    echo ""
    
    check_root
    check_ubuntu
    
    info "Начинается установка Appointment Bot..."
    echo ""
    
    install_dependencies
    create_user
    install_project
    create_services
    create_management_script
    create_sample_config
    final_setup
    
    echo ""
    echo "🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!"
    echo "================================="
    echo ""
    echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
    echo ""
    echo "1. Настройте конфигурацию:"
    echo "   sudo nano /home/appointment-bot/appointment-bot/config/channels.json"
    echo ""
    echo "2. Запустите бота:"
    echo "   sudo appointment-bot-ctl start"
    echo ""
    echo "3. Проверьте статус:"
    echo "   sudo appointment-bot-ctl status"
    echo ""
    echo "4. Просмотр логов:"
    echo "   sudo appointment-bot-ctl logs"
    echo ""
    echo "📖 Полная документация:"
    echo "   https://github.com/Poleno7682/appointment-bot"
    echo ""
    echo "🔧 Управление ботом:"
    echo "   appointment-bot-ctl {start|stop|restart|status|logs|update}"
    echo ""
    echo "✅ Бот готов к настройке и запуску!"
}

# Запуск основной функции
main "$@" 