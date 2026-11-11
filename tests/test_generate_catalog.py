# Тесты генератора каталога Skills.
# Запуск: python3 -m unittest discover -s tests -v
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_catalog as gc  # noqa: E402

GOOD_META = {
    "title_ru": "Создание профессиональных документов",
    "summary_ru": "Создание, переработка, редактирование и аудит деловых документов.",
    "category_ru": "Документы и делопроизводство",
    "status": "published",
    "tags": ["документы", "аудит"],
}

README_TEMPLATE = """# Заголовок

Вводный текст.

<!-- skills-catalog:start -->
СТАРЫЙ БЛОК
<!-- skills-catalog:end -->

## Раздел после каталога

Текст после каталога.
"""


def make_repo(meta_by_name: dict[str, str | dict | None]) -> Path:
    """Собрать временный «репозиторий» с skills/*/catalog.yml и README."""
    root = Path(tempfile.mkdtemp(prefix="catalog-test-"))
    (root / "skills").mkdir()
    for name, meta in meta_by_name.items():
        skill_dir = root / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        if meta is not None:
            body = meta if isinstance(meta, str) else gc.yaml.safe_dump(
                meta, allow_unicode=True
            )
            (skill_dir / "catalog.yml").write_text(body, encoding="utf-8")
    (root / "README.md").write_text(README_TEMPLATE, encoding="utf-8")
    return root


def run_main(root: Path, *argv: str) -> int:
    return gc.main([*argv, "--root", str(root)])


class CatalogTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    # 1. Корректные метаданные дают ожидаемый каталог
    def test_valid_metadata_renders_catalog(self):
        self.root = make_repo({"professional-document-creation": GOOD_META})
        self.assertEqual(run_main(self.root), 0)
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("### Документы и делопроизводство", readme)
        self.assertIn("[`professional-document-creation`](skills/professional-document-creation/)", readme)
        self.assertIn("Создание профессиональных документов", readme)
        self.assertIn("| Готов |", readme)
        self.assertIn("документы, аудит", readme)
        self.assertNotIn("СТАРЫЙ БЛОК", readme)

    # 2. Отсутствует обязательное поле
    def test_missing_required_field_fails(self):
        meta = {k: v for k, v in GOOD_META.items() if k != "summary_ru"}
        self.root = make_repo({"some-skill": meta})
        with self.assertRaises(gc.CatalogError) as ctx:
            gc.load_catalog_data(self.root)
        self.assertIn("summary_ru", str(ctx.exception))

    # 3. YAML некорректен и поле неправильного типа
    def test_broken_yaml_fails(self):
        self.root = make_repo({"some-skill": "title_ru: [unclosed"})
        with self.assertRaises(gc.CatalogError):
            gc.load_catalog_data(self.root)

    def test_wrong_field_type_fails(self):
        self.root = make_repo({"some-skill": {**GOOD_META, "title_ru": 42}})
        with self.assertRaises(gc.CatalogError) as ctx:
            gc.load_catalog_data(self.root)
        self.assertIn("title_ru", str(ctx.exception))

    def test_wrong_tags_type_fails(self):
        self.root = make_repo({"some-skill": {**GOOD_META, "tags": "документы"}})
        with self.assertRaises(gc.CatalogError):
            gc.load_catalog_data(self.root)

    # 4. Неизвестный статус
    def test_unknown_status_fails(self):
        self.root = make_repo({"some-skill": {**GOOD_META, "status": "released"}})
        with self.assertRaises(gc.CatalogError) as ctx:
            gc.load_catalog_data(self.root)
        self.assertIn("released", str(ctx.exception))

    # 5. README обновляется только внутри блока каталога
    def test_only_block_is_replaced(self):
        self.root = make_repo({"some-skill": GOOD_META})
        run_main(self.root)
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# Заголовок\n\nВводный текст."))
        self.assertIn("## Раздел после каталога\n\nТекст после каталога.", readme)

    # 6. --check: устаревший README обнаруживается, актуальный проходит
    def test_check_detects_stale_and_accepts_fresh(self):
        self.root = make_repo({"some-skill": GOOD_META})
        # README ещё со старым блоком
        self.assertEqual(run_main(self.root, "--check"), 1)
        # после генерации --check проходит
        run_main(self.root)
        self.assertEqual(run_main(self.root, "--check"), 0)

    # 7. Символ | и Markdown/HTML-значения не ломают таблицу
    def test_pipe_and_markup_escaped(self):
        meta = {
            **GOOD_META,
            "title_ru": "Название | с вертикальной чертой",
            "summary_ru": "Описание с <b>HTML</b>, `код` и | чертой",
        }
        self.root = make_repo({"some-skill": meta})
        self.assertEqual(run_main(self.root), 0)
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        block = gc.extract_block(readme)
        # каждая строка таблицы содержит ровно 6 разделителей ячеек
        for line in block.splitlines():
            if line.startswith("| [`"):
                self.assertEqual(line.count("|") - line.count("\\|"), 6)
        self.assertIn("\\|", block)
        self.assertIn("&lt;b&gt;", block)
        self.assertNotIn("<b>", block)


if __name__ == "__main__":
    unittest.main()
