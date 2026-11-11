# Pull Request

## Что сделано

<!-- Кратко опишите изменения. -->

## Чек-лист автора Skill / изменения

- [ ] Skill размещён в `skills/<skill-name>/` с валидным `SKILL.md` (YAML frontmatter: `name` совпадает с именем директории, заполнено `description`).
- [ ] Добавлен `skills/<skill-name>/catalog.yml` (по шаблону `templates/catalog.yml`).
- [ ] Метаданные проходят валидацию: `python3 scripts/generate_catalog.py --validate`
- [ ] README перегенерирован: `python3 scripts/generate_catalog.py` (блок между `<!-- skills-catalog:start -->` и `<!-- skills-catalog:end -->` обновлён, остальной README не тронут).
- [ ] `python3 scripts/generate_catalog.py --check` завершается с кодом 0.
- [ ] Тесты проходят: `python3 -m unittest discover -s tests -v`
- [ ] Формат Agent Skills не нарушен: в frontmatter `SKILL.md` нет нестандартных полей.
- [ ] Совместимость платформ заявлена только там, где она подтверждена.

## Проверка CI

<!-- Убедитесь, что job «Каталог Skills» зелёный: метаданные, тесты и --check. -->
