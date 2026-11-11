#!/usr/bin/env python3
"""Генератор русскоязычного каталога Skills для README.md.

Читает `skills/<skill-name>/catalog.yml` для каждого Skill, валидирует
метаданные и обновляет блок каталога в README.md между маркерами:

    <!-- skills-catalog:start -->
    ...
    <!-- skills-catalog:end -->

Режимы:
    python3 scripts/generate_catalog.py           # обновить README
    python3 scripts/generate_catalog.py --check   # только проверить актуальность
    python3 scripts/generate_catalog.py --validate # только валидировать метаданные

Зависимость: PyYAML (requirements.txt). Разбор YAML выполняется безопасным
загрузчиком `yaml.safe_load`, а не разбиением строк.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    print(
        "Ошибка: требуется PyYAML. Установите зависимости: "
        "pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
README_PATH = REPO_ROOT / "README.md"

START_MARKER = "<!-- skills-catalog:start -->"
END_MARKER = "<!-- skills-catalog:end -->"

REQUIRED_FIELDS = ("title_ru", "summary_ru", "category_ru", "status")
ALLOWED_STATUSES = {
    "planned": "Планируется",
    "beta": "Бета",
    "published": "Готов",
    "deprecated": "Устарел",
}


class CatalogError(Exception):
    """Ошибка метаданных каталога с понятным сообщением."""


def validate_skill_file(skill_dir: Path) -> None:
    """Проверить, что SKILL.md соответствует стандарту Agent Skills для данного Skill."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise CatalogError(f"{skill_dir.name}: в директории Skill отсутствует SKILL.md")

    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError(f"{skill_dir.name}: нельзя прочитать SKILL.md — {exc}") from exc

    if not text.startswith("---"):
        raise CatalogError(f"{skill_dir.name}: SKILL.md должен начинаться с YAML frontmatter '---'")

    split_index = text.find("\n---\n", 4)
    if split_index == -1:
        raise CatalogError(f"{skill_dir.name}: SKILL.md должен содержать закрывающий '---' после frontmatter")

    frontmatter_text = text[4:split_index]
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        raise CatalogError(f"{skill_dir.name}: некорректный YAML frontmatter в SKILL.md — {exc}") from exc

    if not isinstance(frontmatter, dict):
        raise CatalogError(f"{skill_dir.name}: YAML frontmatter в SKILL.md должен быть словарём")

    name_value = frontmatter.get("name")
    if not isinstance(name_value, str) or not name_value.strip():
        raise CatalogError(f"{skill_dir.name}: в SKILL.md отсутствует корректное поле 'name'")
    if name_value != skill_dir.name:
        raise CatalogError(
            f"{skill_dir.name}: поле 'name' в SKILL.md должно совпадать с именем директории "
            f"({skill_dir.name}), получено '{name_value}'"
        )

    description_value = frontmatter.get("description")
    if not isinstance(description_value, str) or not description_value.strip():
        raise CatalogError(f"{skill_dir.name}: в SKILL.md отсутствует корректное поле 'description'")


def _load(data: dict[str, Any], path: Path) -> None:
    """Загрузчик по умолчанию (вынесен для подмены в тестах)."""
    with path.open(encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise CatalogError(f"{path}: YAML должен быть словарём, получено {type(loaded).__name__}")
    data.update(loaded)


def load_catalog_data(root: Path, load=_load) -> list[dict[str, Any]]:
    """Собрать и валидировать метаданные всех Skills из каталога root/skills."""
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        raise CatalogError(f"Директория Skills не найдена: {skills_dir}")
    entries: list[dict[str, Any]] = []
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        name = skill_dir.name
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            raise CatalogError(
                f"{name}: в директории Skill нет SKILL.md — это не валидный Skill"
            )
        validate_skill_file(skill_dir)
        catalog_path = skill_dir / "catalog.yml"
        if not catalog_path.is_file():
            raise CatalogError(
                f"{name}: отсутствует catalog.yml. "
                f"Скопируйте шаблон templates/catalog.yml и заполните его."
            )
        meta: dict[str, Any] = {}
        try:
            load(meta, catalog_path)
        except yaml.YAMLError as exc:
            raise CatalogError(f"{name}: некорректный YAML в catalog.yml — {exc}") from exc
        validate_meta(name, meta, catalog_path)
        entries.append({"name": name, **meta})
    return entries


def validate_meta(name: str, meta: dict[str, Any], path: Path | None = None) -> None:
    """Валидация полей одного catalog.yml."""
    where = f"{name}" + (f" ({path.name})" if path else "")
    for field in REQUIRED_FIELDS:
        if field not in meta:
            raise CatalogError(f"{where}: отсутствует обязательное поле «{field}»")
    for field in ("title_ru", "summary_ru", "category_ru"):
        value = meta[field]
        if not isinstance(value, str) or not value.strip():
            raise CatalogError(f"{where}: поле «{field}» должно быть непустой строкой")
    status = meta["status"]
    if status not in ALLOWED_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_STATUSES))
        raise CatalogError(
            f"{where}: недопустимый статус «{status}». Разрешены: {allowed}"
        )
    tags = meta.get("tags")
    if tags is not None:
        if not isinstance(tags, list) or not all(
            isinstance(t, str) and t.strip() for t in tags
        ):
            raise CatalogError(
                f"{where}: поле «tags» должно быть списком непустых строк"
            )
    extra = set(meta) - set(REQUIRED_FIELDS) - {"tags"}
    if extra:
        raise CatalogError(f"{where}: неизвестные поля: {', '.join(sorted(extra))}")


def escape_cell(text: str) -> str:
    """Экранирование значения для ячейки Markdown-таблицы."""
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.strip()


def render_catalog(entries: list[dict[str, Any]]) -> str:
    """Собрать Markdown-блок каталога: категории и Skills отсортированы."""
    if not entries:
        body = "_Каталог пуст: Skills пока не добавлены._\n"
        return f"{START_MARKER}\n{body}{END_MARKER}"
    by_category: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_category.setdefault(entry["category_ru"], []).append(entry)
    lines: list[str] = []
    for category in sorted(by_category):
        lines.append(f"### {category}\n")
        lines.append("| Skill | Название | Описание | Теги | Статус |")
        lines.append("|---|---|---|---|---|")
        for entry in sorted(by_category[category], key=lambda e: e["name"]):
            link = f"[`{entry['name']}`](skills/{entry['name']}/)"
            title = escape_cell(entry["title_ru"])
            summary = escape_cell(entry["summary_ru"])
            tags = escape_cell(", ".join(entry.get("tags") or [])) or "—"
            status = escape_cell(ALLOWED_STATUSES[entry["status"]])
            lines.append(f"| {link} | {title} | {summary} | {tags} | {status} |")
        lines.append("")
    body = "\n".join(lines).rstrip() + "\n"
    return f"{START_MARKER}\n{body}{END_MARKER}"


def replace_block(readme_text: str, block: str) -> str:
    """Заменить содержимое между маркерами, не трогая остальной README."""
    start = readme_text.find(START_MARKER)
    end = readme_text.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise CatalogError(
            "В README.md не найдены маркеры каталога "
            f"{START_MARKER} и {END_MARKER}. Добавьте пустой блок:"
            f"\n{START_MARKER}\n{END_MARKER}"
        )
    return readme_text[:start] + block + readme_text[end + len(END_MARKER) :]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Генератор каталога Skills")
    parser.add_argument(
        "--check",
        action="store_true",
        help="проверить, что каталог в README актуален, не изменяя файлы",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="только валидировать метаданные всех Skills",
    )
    parser.add_argument("--root", type=Path, help="корень репозитория (для тестов)")
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else REPO_ROOT

    try:
        entries = load_catalog_data(root)
    except CatalogError as exc:
        print(f"Ошибка метаданных каталога: {exc}", file=sys.stderr)
        return 1

    if args.validate:
        print(f"Метаданные валидны: Skills — {len(entries)}.")
        return 0

    block = render_catalog(entries)
    readme_path = root / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")

    if args.check:
        current = extract_block(readme_text)
        if current == block:
            print("Каталог в README актуален.")
            return 0
        print(
            "Каталог в README устарел. Запустите: python3 scripts/generate_catalog.py",
            file=sys.stderr,
        )
        return 1

    try:
        updated = replace_block(readme_text, block)
    except CatalogError as exc:
        print(f"Ошибка README: {exc}", file=sys.stderr)
        return 1
    if updated != readme_text:
        readme_path.write_text(updated, encoding="utf-8")
        print(f"README.md обновлён: Skills — {len(entries)}.")
    else:
        print("Каталог в README уже актуален, изменения не требуются.")
    return 0


def extract_block(readme_text: str) -> str:
    """Выделить текущий блок каталога (для сравнения в --check и в тестах)."""
    start = readme_text.find(START_MARKER)
    end = readme_text.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise CatalogError("Маркеры каталога не найдены в README.md")
    return readme_text[start : end + len(END_MARKER)]


if __name__ == "__main__":
    sys.exit(main())
