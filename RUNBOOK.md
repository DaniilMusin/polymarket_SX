# Runbook: Polymarket-SX Arbitrage Bot

## Быстрые действия
- Проверить, что сервис запущен: `docker compose ps` или `systemctl status polymarket-bot`.
- Логи (ротация включена):
  - Общий: `logs/bot.log`
  - Ошибки/алерты: `logs/errors.log`, `logs/alerts.log`
  - Сделки: `logs/trades.log`
- Балансы и экспозиции: запуск `python - <<'PY'\nfrom core.exchange_balances import get_balance_manager\nprint(get_balance_manager().get_all_balances())\nPY`

## Остановка бота
- Docker: `docker compose down`
- systemd: `sudo systemctl stop polymarket-bot`

## Полное закрытие позиций
- Выполнить: `python scripts/close_all_positions.py`
- После выполнения убедиться, что все виртуальные балансы обнулены (см. пункт выше).

## Обновление и рестарт
- `scripts/redeploy.sh` (для Docker) — делает `git pull`, билдит и перезапускает контейнер.

## Диагностика проблем
- Не идут сделки: проверяем `logs/errors.log` и `logs/alerts.log`.
- Подозрение на зависание: смотрим таймстемпы в `logs/bot.log` и ротацию (последние записи). Если нет активности дольше заданного интервала — вручную перезапустить сервис.
- Биржа/API падает: в логах будут ошибки запроса. При множественных ошибках включится panic-режим (см. ошибки/алерты).

## Восстановление после panic-режима
- Найти причину в логах.
- Закрыть экспозицию через `scripts/close_all_positions.py`.
- Перезапустить сервис, убедиться, что panic не активен (лог «Logging configured…» без последующих ошибок о panic).
