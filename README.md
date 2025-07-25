# 🤖 Арбитражный бот для Polymarket и SX

Арбитражный бот для автоматического поиска и выполнения арбитражных сделок между биржами Polymarket и SX.

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Запуск всех проверок
```bash
python run_checks.py
```

### 3. Демо-запуск бота
```bash
python demo_bot.py --cycles 3 --interval 5
```

### 4. Запуск в реальном режиме
```bash
# Тестовый режим (один цикл)
python main_improved.py --test

# Непрерывная работа
python main_improved.py --interval 30
```

## 📋 Требования

- Python 3.8+
- API ключи для Polymarket и SX
- Telegram Bot Token (опционально, для уведомлений)

## 🏗️ Архитектура

```
├── main.py                 # Главный файл запуска
├── config.py              # Конфигурация проскальзывания
├── core/                  # Основная логика
│   ├── processor.py       # Обработка глубины стакана
│   ├── matcher.py         # Сопоставление рынков
│   ├── metrics.py         # Метрики Prometheus
│   └── alerts.py          # Telegram уведомления
├── connectors/            # Подключения к биржам
│   ├── polymarket.py      # API Polymarket
│   └── sx.py              # API SX
├── utils/                 # Утилиты
│   └── retry.py           # Механизм повторных попыток
├── tests/                 # Unit-тесты
└── requirements.txt       # Зависимости
```

## ⚙️ Конфигурация

### Проскальзывание по глубине
```python
SLIP_BY_DEPTH = {
    20000: 0.0005,  # Глубина ≥ 20000: проскальзывание 0.05%
    10000: 0.0010,  # Глубина ≥ 10000: проскальзывание 0.10%
    5000: 0.0020,   # Глубина ≥ 5000: проскальзывание 0.20%
    1000: 0.0050,   # Глубина ≥ 1000: проскальзывание 0.50%
}
```

### Переменные окружения
```bash
# Telegram Bot Token (опционально)
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# API ключи (для реальной работы)
export POLYMARKET_API_KEY="your_polymarket_key"
export SX_API_KEY="your_sx_key"
```

## 🧪 Тестирование

### Запуск всех тестов
```bash
python -m pytest tests/ -v
```

### Отдельные тесты
```bash
# Тесты процессора
python -m pytest tests/test_processor.py -v

# Тесты сопоставления
python -m pytest tests/test_matcher.py -v

# Тесты уведомлений
python -m pytest tests/test_alerts.py -v
```

## 📊 Мониторинг

### Prometheus метрики
- `g_edge` - Счетчик обработанных циклов
- `g_trades` - Счетчик потенциальных сделок

### Логирование
- Уровень: INFO
- Формат: `%(asctime)s - %(levelname)s - %(message)s`
- Telegram уведомления для критических событий

## 🔧 Разработка

### Структура проекта
```
├── main.py                 # Точка входа
├── main_improved.py        # Улучшенная версия с аргументами
├── demo_bot.py             # Демо-версия с моковыми данными
├── run_checks.py           # Скрипт проверок
├── test_bot_logic.py       # Тестирование логики
├── analyze_bot.py          # Анализ логики
└── FINAL_BOT_ANALYSIS.md   # Финальный отчет
```

### Добавление новых бирж
1. Создайте новый файл в `connectors/`
2. Реализуйте функцию `orderbook_depth()`
3. Добавьте импорт в `main.py`
4. Напишите тесты

### Добавление новых метрик
1. Добавьте метрику в `core/metrics.py`
2. Обновите логику в `core/processor.py`
3. Напишите тесты

## 🚨 Безопасность

- Никогда не коммитьте API ключи в репозиторий
- Используйте переменные окружения для секретов
- Регулярно обновляйте зависимости
- Мониторьте логи на предмет подозрительной активности

## 📈 Производительность

### Оптимизации
- Асинхронные HTTP запросы
- Кэширование данных стакана
- Механизм повторных попыток
- Ленивая загрузка метрик

### Мониторинг
- Prometheus метрики
- Telegram уведомления
- Детальное логирование
- Health checks

## 🐛 Устранение неполадок

### Частые проблемы

1. **Ошибка 404 от API**
   - Проверьте правильность ID рынков
   - Убедитесь в актуальности API ключей

2. **Ошибки подключения**
   - Проверьте интернет-соединение
   - Убедитесь в доступности API бирж

3. **Ошибки Telegram**
   - Проверьте правильность Bot Token
   - Убедитесь в корректности Chat ID

### Логи
```bash
# Просмотр логов в реальном времени
tail -f bot.log

# Поиск ошибок
grep "ERROR" bot.log
```

## 📝 Лицензия

MIT License - см. файл LICENSE для деталей.

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📞 Поддержка

- Создайте Issue для багов
- Используйте Discussions для вопросов
- Обратитесь к документации API бирж

---

**Статус**: ✅ Готов к продакшену

**Последнее обновление**: 2025-07-19
