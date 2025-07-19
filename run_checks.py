#!/usr/bin/env python3
"""
Скрипт для быстрого запуска всех проверок арбитражного бота
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command: str, description: str) -> bool:
    """Запускает команду и возвращает True если успешно"""
    print(f"\n🔍 {description}")
    print("=" * 60)
    
    try:
        # Используем bash для выполнения команд с source
        result = subprocess.run(
            f"bash -c '{command}'", 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
            
        success = result.returncode == 0
        status = "✅ УСПЕШНО" if success else "❌ ОШИБКА"
        print(f"\n{status}: {description}")
        
        return success
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False

def main():
    """Главная функция проверок"""
    print("🤖 ПРОВЕРКА АРБИТРАЖНОГО БОТА")
    print("=" * 60)
    
    # Активируем виртуальное окружение
    venv_activate = "source venv/bin/activate && "
    
    checks = [
        # Проверка зависимостей
        (f"{venv_activate}pip list", "Проверка установленных зависимостей"),
        
        # Запуск unit-тестов
        (f"{venv_activate}python -m pytest tests/ -v", "Запуск unit-тестов"),
        
        # Проверка синтаксиса основных файлов
        (f"{venv_activate}python -m py_compile main.py", "Проверка синтаксиса main.py"),
        (f"{venv_activate}python -m py_compile config.py", "Проверка синтаксиса config.py"),
        (f"{venv_activate}python -m py_compile core/processor.py", "Проверка синтаксиса processor.py"),
        (f"{venv_activate}python -m py_compile core/matcher.py", "Проверка синтаксиса matcher.py"),
        (f"{venv_activate}python -m py_compile core/metrics.py", "Проверка синтаксиса metrics.py"),
        (f"{venv_activate}python -m py_compile core/alerts.py", "Проверка синтаксиса alerts.py"),
        (f"{venv_activate}python -m py_compile connectors/polymarket.py", "Проверка синтаксиса polymarket.py"),
        (f"{venv_activate}python -m py_compile connectors/sx.py", "Проверка синтаксиса sx.py"),
        (f"{venv_activate}python -m py_compile utils/retry.py", "Проверка синтаксиса retry.py"),
        
        # Демо-запуск бота
        (f"{venv_activate}python demo_bot.py --cycles 1 --interval 1", "Демо-запуск бота"),
    ]
    
    results = []
    for command, description in checks:
        success = run_command(command, description)
        results.append((description, success))
    
    # Итоговый отчет
    print(f"\n📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {description}")
    
    print(f"\n🎯 РЕЗУЛЬТАТ: {passed}/{total} проверок прошли успешно")
    
    if passed == total:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОШЛИ УСПЕШНО!")
        print("🚀 Бот готов к работе!")
        return 0
    else:
        print("⚠️  Некоторые проверки не прошли. Проверьте ошибки выше.")
        return 1

if __name__ == "__main__":
    sys.exit(main())