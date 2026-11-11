#!/usr/bin/env python3
"""Создание заготовки нового Skill: scripts/new_skill.py <skill-name>.

Создаёт skills/<skill-name>/catalog.yml из шаблона и печатает инструкцию.
Файл SKILL.md не генерируется: полноценный Skill нельзя создать из шаблона
без содержательной работы, а фиктивные файлы в библиотеке запрещены.

Скрипт не перезаписывает существующие файлы и проверяет допустимость имени.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME_LEN = 64  # ограничение поля name спецификации Agent Skills


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Использование: python3 scripts/new_skill.py <skill-name>", file=sys.stderr)
        return 2
    name = argv[0]
    if not NAME_RE.fullmatch(name) or len(name) > MAX_NAME_LEN:
        print(
            f"Ошибка: недопустимое имя «{name}». Имя должно состоять из строчных "
            "латинских букв, цифр и дефисов, без дефисов по краям и подряд, "
            f"не длиннее {MAX_NAME_LEN} символов (требование спецификации Agent Skills).",
            file=sys.stderr,
        )
        return 1
    skill_dir = REPO_ROOT / "skills" / name
    if skill_dir.exists():
        print(f"Ошибка: директория {skill_dir.relative_to(REPO_ROOT)} уже существует.", file=sys.stderr)
        return 1
    template = REPO_ROOT / "templates" / "catalog.yml"
    if not template.is_file():
        print(f"Ошибка: шаблон не найден: {template}", file=sys.stderr)
        return 1

    skill_dir.mkdir(parents=True)
    (skill_dir / "catalog.yml").write_text(
        template.read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(f"Создан каталог метаданных: skills/{name}/catalog.yml")
    print()
    print("Что дальше (Skill без SKILL.md валидатор каталога не пропустит):")
    print(f"  1. Создайте skills/{name}/SKILL.md по спецификации Agent Skills")
    print("     (https://agentskills.io/specification): YAML frontmatter")
    print("     с полями name и description + содержательные инструкции.")
    print(f"     Значение name должно совпадать с именем директории: {name}.")
    print("  2. Заполните skills/" + name + "/catalog.yml (название, описание,")
    print("     категория, статус, теги).")
    print("  3. Проверьте метаданные: python3 scripts/generate_catalog.py --validate")
    print("  4. Обновите README: python3 scripts/generate_catalog.py")
    print("  5. Пройдите чек-лист из шаблона Pull Request (.github/PULL_REQUEST_TEMPLATE.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
