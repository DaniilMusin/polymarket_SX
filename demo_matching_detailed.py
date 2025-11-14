#!/usr/bin/env python3
"""
Детальная демонстрация fuzzy matching с анализом того, почему события совпадают или нет
"""

from datetime import datetime
from dataclasses import dataclass
from rapidfuzz import fuzz

from core.matcher import _normalize, _extract_teams


@dataclass
class MockEvent:
    """Моковое событие для демонстрации"""

    title: str
    t_start: datetime
    platform: str


def analyze_match_score(pm_event: MockEvent, sx_event: MockEvent) -> dict:
    """Детальный анализ того, почему события совпадают или нет"""

    pm_title_norm = _normalize(pm_event.title)
    sx_title_norm = _normalize(sx_event.title)

    pm_teams = _extract_teams(pm_event.title)
    sx_teams = _extract_teams(sx_event.title)

    date_tag = pm_event.t_start.strftime("%Y-%m-%d")

    # Строим comparison strings как в matcher.py
    pm_comparison = " ".join(pm_teams) + " " + date_tag
    sx_comparison = " ".join(sx_teams) + " " + date_tag

    # Различные типы similarity scores
    token_set = fuzz.token_set_ratio(pm_comparison, sx_comparison)
    token_sort = fuzz.token_sort_ratio(pm_comparison, sx_comparison)
    partial = fuzz.partial_ratio(pm_comparison, sx_comparison)
    simple = fuzz.ratio(pm_comparison, sx_comparison)

    return {
        "pm_title": pm_event.title,
        "sx_title": sx_event.title,
        "pm_normalized": pm_title_norm,
        "sx_normalized": sx_title_norm,
        "pm_teams": pm_teams,
        "sx_teams": sx_teams,
        "pm_comparison": pm_comparison,
        "sx_comparison": sx_comparison,
        "token_set_ratio": token_set,
        "token_sort_ratio": token_sort,
        "partial_ratio": partial,
        "simple_ratio": simple,
        "passes_threshold": token_set >= 87,
    }


def print_detailed_analysis():
    """Детальный анализ всех пар событий"""

    polymarket_events = [
        MockEvent(
            "Boston Celtics @ LA Lakers",
            datetime(2024, 12, 25),
            "Polymarket",
        ),
        MockEvent(
            "Will Trump win 2024 election?",
            datetime(2024, 11, 5),
            "Polymarket",
        ),
        MockEvent(
            "Bitcoin above $100k by EOY",
            datetime(2024, 12, 31),
            "Polymarket",
        ),
    ]

    sx_events = [
        MockEvent(
            "Boston Celtics at Los Angeles Lakers",
            datetime(2024, 12, 25),
            "SX",
        ),
        MockEvent(
            "Trump Presidential Victory 2024",
            datetime(2024, 11, 5),
            "SX",
        ),
        MockEvent(
            "BTC reaches $100,000 in 2024",
            datetime(2024, 12, 31),
            "SX",
        ),
    ]

    print("\n" + "=" * 80)
    print("  🔍 ДЕТАЛЬНЫЙ АНАЛИЗ FUZZY MATCHING")
    print("=" * 80)

    for i, pm_event in enumerate(polymarket_events, 1):
        print(f"\n\n📌 POLYMARKET EVENT #{i}:")
        print(f"   {pm_event.title}")
        print(f"   Дата: {pm_event.t_start.date()}")
        print("\n   Анализ совпадений с событиями SX:")
        print("   " + "-" * 76)

        for j, sx_event in enumerate(sx_events, 1):
            result = analyze_match_score(pm_event, sx_event)

            print(f"\n   SX Event #{j}: {sx_event.title}")
            print(f"   {'─' * 72}")
            print(f"   Нормализация:")
            print(f"     PM: '{result['pm_normalized']}'")
            print(f"     SX: '{result['sx_normalized']}'")
            print(f"   Извлеченные команды/ключевые слова:")
            print(f"     PM: {result['pm_teams']}")
            print(f"     SX: {result['sx_teams']}")
            print(f"   Comparison strings (с датой):")
            print(f"     PM: '{result['pm_comparison']}'")
            print(f"     SX: '{result['sx_comparison']}'")
            print(f"\n   Similarity Scores:")
            print(f"     Token Set Ratio:  {result['token_set_ratio']}% {'✅' if result['token_set_ratio'] >= 87 else '❌'}")
            print(f"     Token Sort Ratio: {result['token_sort_ratio']}%")
            print(f"     Partial Ratio:    {result['partial_ratio']}%")
            print(f"     Simple Ratio:     {result['simple_ratio']}%")

            if result["passes_threshold"]:
                print(f"\n   ✅ MATCH! (score {result['token_set_ratio']}% >= 87%)")
            else:
                print(f"\n   ❌ NO MATCH (score {result['token_set_ratio']}% < 87%)")

                # Объясняем, почему не совпало
                if result["simple_ratio"] < 50:
                    print("   💡 Причина: Слишком разные формулировки")
                elif result["partial_ratio"] >= 70 and result["token_set_ratio"] < 87:
                    print("   💡 Причина: Есть общие слова, но структура разная")
                else:
                    print("   💡 Причина: Недостаточно общих токенов")

    # Рекомендации
    print("\n\n" + "=" * 80)
    print("  💡 РЕКОМЕНДАЦИИ ДЛЯ УЛУЧШЕНИЯ MATCHING")
    print("=" * 80)
    print("""
1. Для спортивных событий:
   ✅ Использование '@' работает хорошо
   ⚠️  Проблема: 'LA Lakers' vs 'Los Angeles Lakers'
   🔧 Решение: Добавить синонимы команд в словарь

2. Для политических событий:
   ❌ 'Will Trump win 2024 election?' vs 'Trump Presidential Victory 2024'
   🔧 Решение: Снизить порог до 80% или использовать Perplexity API

3. Для криптовалютных событий:
   ❌ 'Bitcoin above $100k by EOY' vs 'BTC reaches $100,000 in 2024'
   🔧 Решение:
      - Добавить синонимы: 'Bitcoin' <-> 'BTC'
      - 'above $100k' <-> 'reaches $100,000'
      - 'by EOY' <-> 'in 2024'

4. Общие улучшения:
   ✅ Использовать Perplexity API для событий с score 70-86%
   ✅ Создать словарь синонимов для популярных терминов
   ✅ Учитывать description, не только title
   ✅ Добавить категории событий (sport, politics, crypto, etc.)
""")

    print("\n" + "=" * 80)
    print("  🔍 ПОЧЕМУ MATCHER.PY НАШЕЛ ТОЛЬКО 1 ПА��У?")
    print("=" * 80)
    print("""
Функция _extract_teams() работает только для спортивных событий с '@':
  ✅ "Boston Celtics @ LA Lakers" → ('boston celtics', 'la lakers')
  ❌ "Will Trump win 2024 election?" → ('will trump win 2024 election?', '')
  ❌ "Bitcoin above $100k by EOY" → ('bitcoin above $100k by eoy', '')

Для не-спортивных событий второй элемент tuple пустой, что снижает score!

РЕШЕНИЕ:
  1. Использовать весь title если нет '@', а не разбивать на tuple
  2. Или адаптировать логику для разных типов событий
  3. Или использовать Perplexity API для проблемных случаев
""")


if __name__ == "__main__":
    print_detailed_analysis()
