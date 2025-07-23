#!/bin/bash

# 🚀 Полное обновление Appointment Bot на сервере
# Использование: wget https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/update-server.sh && chmod +x update-server.sh && sudo ./update-server.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
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

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Этот скрипт должен запускаться от root. Используйте sudo."
    fi
}

echo "🚀 Appointment Bot - Полное обновление сервера"
echo "=============================================="
echo ""

check_root

# Проверяем существование проекта
PROJECT_DIR="/home/appointment-bot/appointment-bot"
if [ ! -d "$PROJECT_DIR" ]; then
    error "Проект не найден в $PROJECT_DIR. Сначала выполните установку."
fi

log "Останавливаем бота..."
systemctl stop appointment-bot || warn "Бот уже остановлен"

log "Создаем резервную копию текущих конфигураций..."
BACKUP_DIR="/tmp/appointment-bot-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Сохраняем пользовательские конфигурации
if [ -f "$PROJECT_DIR/config/settings.json" ]; then
    cp "$PROJECT_DIR/config/settings.json" "$BACKUP_DIR/"
    log "✓ Сохранен settings.json"
fi

if [ -f "$PROJECT_DIR/config/channels.json" ]; then
    cp "$PROJECT_DIR/config/channels.json" "$BACKUP_DIR/"
    log "✓ Сохранен channels.json"
fi

log "Обновление основных файлов проекта..."
cd "$PROJECT_DIR"

# Список файлов для обновления
declare -a FILES=(
    "main.py"
    "requirements.txt"
    "src/appointment_service.py"
    "src/utils.py"
    "src/telegram_service.py"
    "src/config_manager.py"
    "config/settings.json.example"
    "config/channels.json.example"
    "config/README.md"
    "README.md"
    "INSTALL.md"
    "CONTRIBUTING.md"
    "LICENSE"
    ".gitignore"
)

# Скачиваем обновленные файлы
for file in "${FILES[@]}"; do
    FILE_DIR=$(dirname "$file")
    if [ "$FILE_DIR" != "." ]; then
        sudo -u appointment-bot mkdir -p "$FILE_DIR"
    fi
    
    log "Обновление $file..."
    sudo -u appointment-bot wget -q -O "${file}.new" "https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/$file"
    
    if [ -f "${file}.new" ] && [ -s "${file}.new" ]; then
        sudo -u appointment-bot mv "${file}.new" "$file"
        log "✓ Обновлен: $file"
    else
        warn "✗ Ошибка обновления: $file"
        rm -f "${file}.new"
    fi
done

log "Обновление скрипта управления appointment-bot-ctl..."
wget -q -O /tmp/install.sh "https://raw.githubusercontent.com/Poleno7682/appointment-bot/main/install.sh"

if [ -f /tmp/install.sh ] && [ -s /tmp/install.sh ]; then
    # Извлекаем новый скрипт управления из install.sh
    sed -n '/^cat > \/usr\/local\/bin\/appointment-bot-ctl << '\''EOF'\''$/,/^EOF$/p' /tmp/install.sh | \
    sed '1d;$d' > /tmp/appointment-bot-ctl.new
    
    if [ -s /tmp/appointment-bot-ctl.new ]; then
        mv /tmp/appointment-bot-ctl.new /usr/local/bin/appointment-bot-ctl
        chmod +x /usr/local/bin/appointment-bot-ctl
        log "✓ Обновлен appointment-bot-ctl"
    else
        warn "✗ Ошибка извлечения appointment-bot-ctl"
    fi
else
    warn "✗ Ошибка скачивания install.sh"
fi

rm -f /tmp/install.sh

log "Восстановление пользовательских конфигураций..."
# Восстанавливаем пользовательские настройки
if [ -f "$BACKUP_DIR/settings.json" ]; then
    sudo -u appointment-bot cp "$BACKUP_DIR/settings.json" "$PROJECT_DIR/config/"
    log "✓ Восстановлен settings.json"
else
    # Создаем из шаблона если нет пользовательского
    if [ -f "$PROJECT_DIR/config/settings.json.example" ]; then
        sudo -u appointment-bot cp "$PROJECT_DIR/config/settings.json.example" "$PROJECT_DIR/config/settings.json"
        log "✓ Создан settings.json из шаблона"
    fi
fi

if [ -f "$BACKUP_DIR/channels.json" ]; then
    sudo -u appointment-bot cp "$BACKUP_DIR/channels.json" "$PROJECT_DIR/config/"
    log "✓ Восстановлен channels.json"
else
    # Создаем из шаблона если нет пользовательского
    if [ -f "$PROJECT_DIR/config/channels.json.example" ]; then
        sudo -u appointment-bot cp "$PROJECT_DIR/config/channels.json.example" "$PROJECT_DIR/config/channels.json"
        log "✓ Создан channels.json из шаблона"
    fi
fi

log "Обновление Python зависимостей..."
sudo -u appointment-bot ./venv/bin/pip install --upgrade pip
sudo -u appointment-bot ./venv/bin/pip install -r requirements.txt

log "Проверка установленных пакетов..."
sudo -u appointment-bot ./venv/bin/pip list | grep -E "(aiohttp|requests|selenium)" || true

log "Проверка файлов проекта..."
REQUIRED_FILES=(
    "$PROJECT_DIR/main.py"
    "$PROJECT_DIR/src/utils.py"
    "$PROJECT_DIR/src/telegram_service.py"
    "$PROJECT_DIR/src/appointment_service.py"
    "$PROJECT_DIR/src/config_manager.py"
    "$PROJECT_DIR/requirements.txt"
    "$PROJECT_DIR/config/settings.json"
    "$PROJECT_DIR/config/channels.json"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        log "✓ $file"
    else
        error "✗ Отсутствует критически важный файл: $file"
    fi
done

log "Обновление прав доступа..."
chown -R appointment-bot:appointment-bot "$PROJECT_DIR"
chmod +x "$PROJECT_DIR/main.py"

log "Перезагрузка systemd и запуск бота..."
systemctl daemon-reload
systemctl start appointment-bot

# Ждем 3 секунды и проверяем статус
sleep 3
if systemctl is-active --quiet appointment-bot; then
    log "✅ Бот успешно запущен!"
else
    warn "⚠️ Бот не запустился, проверьте конфигурацию"
    info "Используйте: sudo appointment-bot-ctl logs"
fi

echo ""
echo "🎉 ПОЛНОЕ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!"
echo "==============================="
echo ""
echo "📋 ОБНОВЛЕННЫЕ КОМПОНЕНТЫ:"
echo "  ✅ Все исходные файлы проекта"
echo "  ✅ Скрипт управления appointment-bot-ctl"
echo "  ✅ Python зависимости"
echo "  ✅ Шаблоны конфигураций"
echo "  ✅ Документация"
echo ""
echo "💾 РЕЗЕРВНАЯ КОПИЯ: $BACKUP_DIR"
echo ""
echo "🔧 УПРАВЛЕНИЕ БОТОМ:"
echo "  sudo appointment-bot-ctl status   # Статус"
echo "  sudo appointment-bot-ctl logs     # Логи"
echo "  sudo appointment-bot-ctl restart  # Перезапуск"
echo ""
echo "⚙️ НАСТРОЙКА:"
echo "  sudo nano $PROJECT_DIR/config/channels.json"
echo "  sudo nano $PROJECT_DIR/config/settings.json"
echo ""
echo "✅ Проект полностью обновлен и готов к работе!" 