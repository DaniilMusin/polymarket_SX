# Миграция с Telegram на File-Based Logging

## Что изменилось

### ❌ УДАЛЕНО
- Telegram bot интеграция
- Зависимость `python-telegram-bot` (вызывала проблемы совместимости)
- Переменные окружения: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
- Класс `TelegramHandler`

### ✅ ДОБАВЛЕНО
- `CriticalAlertHandler` - файловое логирование с ротацией
- Логирование всех критических ошибок в `logs/alerts.log`
- Автоматическая ротация файлов (10MB max, 5 бэкапов)
- Новая функция `setup_alert_logging()` для простой настройки

## Преимущества нового подхода

| Telegram Bot | File-Based Logging |
|--------------|-------------------|
| ❌ Зависимость от внешнего API | ✅ Локальное, надёжное |
| ❌ Нужен токен и chat_id | ✅ Работает из коробки |
| ❌ Проблемы совместимости | ✅ Стандартная библиотека Python |
| ❌ Может не доставить сообщения | ✅ Всегда записывает |
| ❌ Сложнее мониторить | ✅ Просто: `tail -f logs/alerts.log` |

## Как использовать

### Базовое использование (автоматически)
Все ошибки уровня ERROR и выше автоматически пишутся в `logs/alerts.log`:

```python
import logging

# Это автоматически попадёт в alerts.log
logging.error("Critical issue: %s", error_message)
logging.critical("System failure!")
```

### Настройка в своём коде
```python
from core.alerts import setup_alert_logging

# Настроить alert logging для вашего logger
logger = logging.getLogger('my_app')
setup_alert_logging(logger)
```

### Мониторинг алертов в реальном времени
```bash
# Смотреть алерты в реальном времени
tail -f logs/alerts.log

# Поиск конкретных ошибок
grep "CRITICAL" logs/alerts.log

# Последние 50 алертов
tail -50 logs/alerts.log
```

## Конфигурация

### Переменные окружения

```bash
# Путь к файлу логов (default: logs/alerts.log)
ALERT_LOG_PATH=logs/alerts.log

# Максимальный размер файла в байтах (default: 10MB)
ALERT_LOG_MAX_BYTES=10485760

# Количество бэкап файлов (default: 5)
ALERT_LOG_BACKUP_COUNT=5
```

### Ротация файлов

При достижении `ALERT_LOG_MAX_BYTES`:
- `alerts.log` → `alerts.log.1`
- `alerts.log.1` → `alerts.log.2`
- и т.д. до `ALERT_LOG_BACKUP_COUNT`

Старые файлы автоматически удаляются.

## Формат логов

```
2025-11-18 15:30:45 | ERROR    | Trade execution failed: insufficient balance
2025-11-18 15:31:12 | CRITICAL | System shutdown: unhandled exception
```

Формат: `timestamp | level | message`

## Миграция с Telegram

### Шаг 1: Удалите старые переменные
```bash
# Из .env удалите:
# TELEGRAM_TOKEN=...
# TELEGRAM_CHAT_ID=...
```

### Шаг 2: (Опционально) Настройте путь к логам
```bash
# В .env добавьте (если хотите изменить default):
ALERT_LOG_PATH=/custom/path/alerts.log
ALERT_LOG_MAX_BYTES=20971520  # 20MB
ALERT_LOG_BACKUP_COUNT=10
```

### Шаг 3: Начните использовать
Всё! Больше ничего не нужно. Алерты автоматически пишутся в файл.

## Интеграция с другими системами

### Отправка алертов в Slack/Discord/Email

Можно легко добавить дополнительные handler'ы:

```python
from core.alerts import CriticalAlertHandler
import logging

# Ваш custom handler для Slack
class SlackHandler(logging.Handler):
    def emit(self, record):
        # Отправить в Slack webhook
        pass

# Добавить к root logger
logger = logging.getLogger()
logger.addHandler(SlackHandler())
```

### Мониторинг с помощью systemd/journald

```bash
# Если запускаете через systemd, логи попадут в journal
journalctl -u your-bot-service -f | grep ERROR
```

### Централизованное логирование (ELK, Splunk)

Просто направьте `logs/alerts.log` в ваш log aggregator:

```bash
# Filebeat, Fluentd, или любой другой shipper
filebeat -e -c filebeat.yml
```

## Устранение проблем

### Логи не создаются

Проверьте права доступа:
```bash
mkdir -p logs
chmod 755 logs
```

### Файл не ротируется

Проверьте конфигурацию:
```python
import os
print(os.getenv('ALERT_LOG_MAX_BYTES', '10485760'))
```

### Нужен старый Telegram функционал

Можно добавить отдельный handler параллельно:
```python
# Установите python-telegram-bot отдельно
# pip install python-telegram-bot

# Создайте свой TelegramHandler
# (код из старой версии core/alerts.py)
```

## Тестирование

Запустите тесты:
```bash
pytest tests/test_alerts.py -v
```

Должно пройти 4/4 теста:
- ✅ test_alert_handler_creation
- ✅ test_alert_handler_emit
- ✅ test_setup_alert_logging
- ✅ test_alert_handler_handles_errors

## Вопросы и поддержка

Если у вас возникли проблемы:
1. Проверьте, что директория `logs/` существует
2. Проверьте права доступа
3. Посмотрите в основные логи приложения
4. Создайте issue в репозитории

---

**Дата миграции:** 2025-11-18
**Версия:** После коммита "Remove Telegram dependency"
