# Как применить патчи

## Созданные файлы

В директории проекта есть 3 патч-файла:

1. **all-changes.patch** (19KB) - один файл со всеми изменениями
2. **0001-Remove-Telegram-dependency-and-implement-simple-file.patch** - коммит 1
3. **0002-Add-migration-guide-and-ignore-logs-directory.patch** - коммит 2

## Способ 1: Применить все изменения сразу (РЕКОМЕНДУЕТСЯ)

```bash
cd /home/user/polymarket_SX

# Применить патч со всеми изменениями
git apply all-changes.patch

# Проверить что применилось
git status

# Закоммитить изменения
git add -A
git commit -m "Remove Telegram dependency and implement file-based logging

- Replace Telegram bot with simple file-based logging system
- Add CriticalAlertHandler with rotating file handler
- Update .env.example with new configuration options
- Add migration guide TELEGRAM_TO_LOGGING_MIGRATION.md
- Remove python-telegram-bot dependency
- Update tests for new logging system"

# Запушить когда сервер заработает
git push -u origin claude/fix-all-errors-01VxkwGeBf46KGqruhZaiXjJ
```

## Способ 2: Применить коммиты по отдельности

```bash
cd /home/user/polymarket_SX

# Применить первый коммит
git am 0001-Remove-Telegram-dependency-and-implement-simple-file.patch

# Применить второй коммит
git am 0002-Add-migration-guide-and-ignore-logs-directory.patch

# Запушить когда сервер заработает
git push -u origin claude/fix-all-errors-01VxkwGeBf46KGqruhZaiXjJ
```

## Способ 3: Просмотр изменений перед применением

```bash
# Просмотреть что изменится
git apply --stat all-changes.patch

# Проверить без применения (dry-run)
git apply --check all-changes.patch

# Применить
git apply all-changes.patch
```

## Что изменено

### Изменённые файлы:
- `.env.example` - обновлена конфигурация (удалён Telegram, добавлены новые опции)
- `.gitignore` - добавлена директория `logs/`
- `core/alerts.py` - полностью переписан (Telegram → file logging)
- `requirements.txt` - удалена зависимость `python-telegram-bot`
- `tests/test_alerts.py` - переписаны тесты

### Новые файлы:
- `TELEGRAM_TO_LOGGING_MIGRATION.md` - подробная документация миграции

## Проверка после применения

```bash
# 1. Проверить синтаксис Python
python3 -m py_compile core/alerts.py

# 2. Запустить тесты
pytest tests/test_alerts.py -v

# 3. Проверить все тесты
pytest tests/ -v

# 4. Проверить что всё работает
python3 -c "from core.alerts import CriticalAlertHandler, setup_alert_logging; print('✓ OK')"
```

## Если возникли проблемы

### Конфликты при применении патча

```bash
# Отменить частично применённый патч
git apply --reverse all-changes.patch

# Или сбросить изменения
git reset --hard HEAD
git clean -fd

# Попробовать с --3way для разрешения конфликтов
git apply --3way all-changes.patch
```

### Проверка текущего состояния

```bash
# Посмотреть что изменено
git diff

# Посмотреть статус
git status

# Посмотреть историю коммитов
git log --oneline -5
```

## После успешного применения

1. Обновите `.env` файл (удалите TELEGRAM_* переменные)
2. Прочитайте `TELEGRAM_TO_LOGGING_MIGRATION.md`
3. Запустите тесты для проверки
4. Запушите изменения когда git-сервер станет доступен

---

**Дата создания патчей:** 2025-11-18
**Ветка:** claude/fix-all-errors-01VxkwGeBf46KGqruhZaiXjJ
**Всего изменений:** 6 файлов (5 изменённых, 1 новый)
