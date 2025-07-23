#!/bin/bash

# Скрипт для полного обновления проекта на сервере
# Включает новую логику немедленного обновления last_registered_date

set -e

echo "🚀 Запуск полного обновления appointment-bot..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка что запущено от root
if [ "$EUID" -ne 0 ]; then
    print_error "Запустите скрипт от имени root: sudo ./update-server.sh"
    exit 1
fi

# Остановка сервиса
print_status "Остановка appointment-bot сервиса..."
if systemctl is-active --quiet appointment-bot; then
    systemctl stop appointment-bot
    print_success "Сервис остановлен"
else
    print_warning "Сервис уже остановлен"
fi

# Переход в рабочую директорию
BOT_DIR="/home/appointment-bot/appointment-bot"
if [ -d "$BOT_DIR" ]; then
    cd "$BOT_DIR"
    print_success "Переход в директорию: $BOT_DIR"
else
    print_error "Директория $BOT_DIR не найдена!"
    exit 1
fi

# Создание резервной копии конфигураций
print_status "Создание резервной копии конфигураций..."
BACKUP_DIR="/home/appointment-bot/config-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "config/channels.json" ]; then
    cp "config/channels.json" "$BACKUP_DIR/"
    print_success "Сохранен channels.json"
fi

if [ -f "config/settings.json" ]; then
    cp "config/settings.json" "$BACKUP_DIR/"
    print_success "Сохранен settings.json"
fi

# Обновление кода
print_status "Обновление исходного кода..."

# Проверяем наличие git
if command -v git &> /dev/null && [ -d ".git" ]; then
    print_status "Обновление через Git..."
    git stash push -m "Backup before update $(date)" || true
    git pull origin master
    print_success "Код обновлен через Git"
else
    print_status "Git не найден, загрузка файлов напрямую..."
    
    # Список файлов для обновления (включая новую логику)
    FILES=(
        "src/appointment_service.py"
        "src/config_manager.py"
        "src/telegram_service.py"
        "src/utils.py"
        "main.py"
        "requirements.txt"
        "install.sh"
        "update-server.sh"
    )
    
    for file in "${FILES[@]}"; do
        if curl -f -s -o "$file.tmp" "https://raw.githubusercontent.com/username/appointment-bot/master/$file"; then
            mv "$file.tmp" "$file"
            print_success "Обновлен: $file"
        else
            print_warning "Не удалось обновить: $file"
            rm -f "$file.tmp"
        fi
    done
fi

# Восстановление конфигураций
print_status "Восстановление конфигураций пользователя..."
if [ -f "$BACKUP_DIR/channels.json" ]; then
    cp "$BACKUP_DIR/channels.json" "config/"
    print_success "Восстановлен channels.json"
fi

if [ -f "$BACKUP_DIR/settings.json" ]; then
    cp "$BACKUP_DIR/settings.json" "config/"
    print_success "Восстановлен settings.json"
fi

# Обновление зависимостей
print_status "Обновление Python зависимостей..."
if [ -f "/home/appointment-bot/venv/bin/activate" ]; then
    source /home/appointment-bot/venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "Зависимости обновлены"
else
    print_error "Виртуальное окружение не найдено!"
    exit 1
fi

# Установка прав доступа
print_status "Установка прав доступа..."
chown -R appointment-bot:appointment-bot /home/appointment-bot/
chmod +x /home/appointment-bot/appointment-bot/main.py
chmod +x /usr/local/bin/appointment-bot-ctl
print_success "Права доступа установлены"

# Перезапуск сервиса
print_status "Запуск обновленного сервиса..."
systemctl daemon-reload
systemctl start appointment-bot
systemctl enable appointment-bot

# Проверка статуса
sleep 3
if systemctl is-active --quiet appointment-bot; then
    print_success "✅ Сервис успешно запущен с новой логикой!"
else
    print_error "❌ Ошибка запуска сервиса"
    systemctl status appointment-bot
    exit 1
fi

print_success "🎉 Обновление завершено успешно!"
print_status "📊 Новые возможности:"
echo "  ✅ Немедленное обновление last_registered_date при достижении лимита"
echo "  ✅ Обновление даты даже при отсутствии доступных времен"
echo "  ✅ Улучшенное логирование процесса регистрации"
echo "  ✅ Предотвращение повторной обработки тех же дат"

print_status "📋 Команды для мониторинга:"
echo "  sudo appointment-bot-ctl status   # Статус сервиса"
echo "  sudo appointment-bot-ctl logs     # Логи в реальном времени"
echo "  sudo journalctl -u appointment-bot --since '1 hour ago' | grep 'last_registered_date'"

print_status "📁 Резервная копия конфигураций сохранена в: $BACKUP_DIR" 