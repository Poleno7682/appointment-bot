#!/bin/bash

# Appointment Bot Deployment Script for Ubuntu
# Автоматическое развертывание и настройка сервиса

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Переменные
PROJECT_NAME="appointment_bot"
SERVICE_USER="appointment"
INSTALL_DIR="/opt/$PROJECT_NAME"
LOG_DIR="/var/log/$PROJECT_NAME"
SERVICE_FILE="/etc/systemd/system/$PROJECT_NAME.service"

# Функции для вывода
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Этот скрипт должен запускаться с правами root"
        log_info "Используйте: sudo $0"
        exit 1
    fi
}

# Обновление системы
update_system() {
    log_info "Обновление системы Ubuntu..."
    apt-get update
    apt-get upgrade -y
    log_success "Система обновлена"
}

# Установка зависимостей системы
install_system_dependencies() {
    log_info "Установка системных зависимостей..."
    
    # Python и pip
    apt-get install -y python3 python3-pip python3-venv
    
    # Chrome и ChromeDriver
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
    apt-get update
    apt-get install -y google-chrome-stable
    
    # ChromeDriver
    apt-get install -y chromium-chromedriver
    
    # Дополнительные пакеты
    apt-get install -y curl wget unzip xvfb
    
    log_success "Системные зависимости установлены"
}

# Создание пользователя для сервиса
create_service_user() {
    log_info "Создание пользователя сервиса..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd --system --home-dir "$INSTALL_DIR" --shell /bin/false "$SERVICE_USER"
        log_success "Пользователь $SERVICE_USER создан"
    else
        log_warning "Пользователь $SERVICE_USER уже существует"
    fi
}

# Создание директорий
create_directories() {
    log_info "Создание директорий..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$LOG_DIR"
    
    # Права доступа
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    
    log_success "Директории созданы"
}

# Копирование файлов проекта
copy_project_files() {
    log_info "Копирование файлов проекта..."
    
    # Проверяем, что мы в директории с проектом
    if [[ ! -f "main.py" ]] || [[ ! -d "src" ]] || [[ ! -d "config" ]]; then
        log_error "Файлы проекта не найдены. Убедитесь, что вы запускаете скрипт из директории проекта."
        exit 1
    fi
    
    # Копируем все файлы
    cp -r . "$INSTALL_DIR/"
    
    # Устанавливаем права
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chmod +x "$INSTALL_DIR/main.py"
    
    log_success "Файлы проекта скопированы"
}

# Создание виртуального окружения и установка зависимостей
setup_python_environment() {
    log_info "Настройка Python окружения..."
    
    cd "$INSTALL_DIR"
    
    # Создаем виртуальное окружение
    sudo -u "$SERVICE_USER" python3 -m venv venv
    
    # Активируем и устанавливаем зависимости
    sudo -u "$SERVICE_USER" bash -c "source venv/bin/activate && pip install --upgrade pip"
    sudo -u "$SERVICE_USER" bash -c "source venv/bin/activate && pip install -r requirements.txt"
    
    log_success "Python окружение настроено"
}

# Настройка конфигурации
setup_configuration() {
    log_info "Настройка конфигурации..."
    
    # Проверяем наличие конфигурационных файлов
    if [[ ! -f "$INSTALL_DIR/config/settings.json" ]]; then
        log_error "Файл config/settings.json не найден"
        exit 1
    fi
    
    if [[ ! -f "$INSTALL_DIR/config/channels.json" ]]; then
        log_error "Файл config/channels.json не найден"
        exit 1
    fi
    
    # Запрашиваем email у пользователя
    read -p "Введите email для регистрации: " user_email
    if [[ -n "$user_email" ]]; then
        sed -i "s/\"email\": \"\"/\"email\": \"$user_email\"/" "$INSTALL_DIR/config/settings.json"
        log_success "Email настроен: $user_email"
    fi
    
    log_warning "Не забудьте настроить Telegram токены в config/channels.json"
    log_success "Базовая конфигурация завершена"
}

# Создание systemd сервиса
create_systemd_service() {
    log_info "Создание systemd сервиса..."
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Appointment Bot - UM Poznan Registration Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/service.log
StandardError=append:$LOG_DIR/error.log

# Environment variables
Environment=PYTHONPATH=$INSTALL_DIR
Environment=DISPLAY=:99

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR $LOG_DIR

# Resource limits
LimitNOFILE=65536
MemoryLimit=512M

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$PROJECT_NAME"
    
    log_success "Systemd сервис создан и включен в автозагрузку"
}

# Создание скрипта управления
create_management_script() {
    log_info "Создание скрипта управления..."
    
    cat > "/usr/local/bin/${PROJECT_NAME}-ctl" << 'EOF'
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
        echo ""
        echo "Команды:"
        echo "  start    - Запустить сервис"
        echo "  stop     - Остановить сервис"
        echo "  restart  - Перезапустить сервис"
        echo "  status   - Показать статус сервиса"
        echo "  logs     - Показать логи сервиса"
        echo "  errors   - Показать логи ошибок"
        echo "  config   - Редактировать конфигурацию"
        exit 1
        ;;
esac
EOF

    chmod +x "/usr/local/bin/${PROJECT_NAME}-ctl"
    log_success "Скрипт управления создан: ${PROJECT_NAME}-ctl"
}

# Настройка Xvfb для headless Chrome
setup_xvfb() {
    log_info "Настройка Xvfb для headless режима..."
    
    cat > "/etc/systemd/system/xvfb.service" << EOF
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

    systemctl daemon-reload
    systemctl enable xvfb
    systemctl start xvfb
    
    log_success "Xvfb настроен и запущен"
}

# Финальная проверка
final_check() {
    log_info "Выполнение финальной проверки..."
    
    # Проверяем статус сервиса
    if systemctl is-enabled "$PROJECT_NAME" >/dev/null 2>&1; then
        log_success "✓ Сервис добавлен в автозагрузку"
    else
        log_error "✗ Сервис НЕ добавлен в автозагрузку"
    fi
    
    # Проверяем файлы
    if [[ -f "$SERVICE_FILE" ]]; then
        log_success "✓ Systemd сервис создан"
    else
        log_error "✗ Systemd сервис НЕ создан"
    fi
    
    if [[ -d "$INSTALL_DIR/venv" ]]; then
        log_success "✓ Python окружение создано"
    else
        log_error "✗ Python окружение НЕ создано"
    fi
    
    log_success "Проверка завершена"
}

# Главная функция
main() {
    echo "=================================================="
    echo "   Appointment Bot - Скрипт развертывания"
    echo "=================================================="
    echo ""
    
    check_root
    update_system
    install_system_dependencies
    create_service_user
    create_directories
    copy_project_files
    setup_python_environment
    setup_configuration
    setup_xvfb
    create_systemd_service
    create_management_script
    final_check
    
    echo ""
    echo "=================================================="
    log_success "Развертывание завершено успешно!"
    echo "=================================================="
    echo ""
    echo "Следующие шаги:"
    echo "1. Настройте Telegram токены в файле:"
    echo "   nano $INSTALL_DIR/config/channels.json"
    echo ""
    echo "2. Запустите сервис:"
    echo "   $PROJECT_NAME-ctl start"
    echo ""
    echo "3. Проверьте статус:"
    echo "   $PROJECT_NAME-ctl status"
    echo ""
    echo "4. Просмотр логов:"
    echo "   $PROJECT_NAME-ctl logs"
    echo ""
    echo "Управление сервисом: $PROJECT_NAME-ctl"
    echo "Логи: $LOG_DIR/"
    echo ""
}

# Запуск
main "$@" 