# Universal Prompt Optimizer v5.11

[English version](README.md)

## Что нового в v5.11

- Добавлена точная маршрутизация и профиль для GPT-6.1 Sol (`gpt-6.1-sol`).
- Добавлена точная маршрутизация и отдельный prompt-профиль для Claude Sonnet 5.5 (`claude-sonnet-5.5`, alias `claude-sonnet-5-5`).
- Обновлены рекомендации для всех поддерживаемых моделей Claude на основе актуальных Anthropic Prompting Best Practices: ограниченная автономность, полезный прогресс при работе с инструментами, порядок long-context данных, уместные examples/XML, проверка поведения и отсутствие скрытого CoT.
- Новые профили распространены на все восемь адаптеров: OpenCode, Pi, Gemini CLI, Cursor, Claude Code, Codex, GitHub Copilot CLI и Windsurf.
- Gemini CLI теперь распознаёт поддерживаемые model ID OpenAI и Claude после наблюдения за фактической моделью, сохраняя нейтральный fallback для неизвестных и неоднозначных ID.
- Добавлены тесты маршрутизации и installer-проверки; registry теперь содержит 26 профилей моделей.

Полное описание изменений: [CHANGELOG.md](CHANGELOG.md).

## Что нового в v5.10

- Добавлен компактный цветной индикатор OpenCode TUI: `● PO AUTO`,
  `◐ PO PREVIEW`, `○ PO OFF`, `◇ PO GENERIC` и `! PO CONFIG`.
- Добавлены настройки через стандартную палитру OpenCode:
  **Ctrl+P → Prompt Optimizer · Settings**.
- Настройки можно сохранять для текущей сессии, проекта или глобально.
- Добавлена атомарная запись конфигурации с защитой от symlink-подмены,
  сохранением пользовательских JSON-полей и безопасной обработкой ошибок.
- Добавлен bridge состояния между TUI и серверным OpenCode plugin без лишнего
  обращения к модели.

Полная история изменений: [CHANGELOG.md](CHANGELOG.md).

## Что делает проект

Universal Prompt Optimizer — это слой предварительной адаптации prompt для
coding-agent систем. Он сохраняет исходный смысл запроса и добавляет только
полезные для выполнения границы: контекст, ограничения, критерии готовности,
формат результата и approval boundaries.

Оптимизация выполняется адаптивно: короткий и точный запрос может пройти без
изменений, а сложная, неоднозначная или рискованная задача получает более
строгое execution-описание. Отдельный optimizer LLM-вызов не требуется.

## Поддерживаемые агенты

| Агент | Интеграция | Точная маршрутизация модели | AUTO | PREVIEW | OFF |
|---|---|---:|---:|---:|---:|
| OpenCode | native server plugin + TUI | Да | Native | Advisory | Да |
| Pi | native extension | Да | Native | Native | Да |
| Cursor | hooks + rule | Да, если модель передана runtime | Да | Question/fallback | Да |
| Gemini CLI | hooks + `GEMINI.md` | Best effort | Да | `ask_user`/fallback | Да |
| Claude Code | skill + `CLAUDE.md` | Семейство Claude | Да | Question/fallback | Да |
| GitHub Copilot CLI | instructions | Best effort | Да | Interactive/fallback | Да |
| OpenAI Codex | `AGENTS.md` | Best effort | Да | Fallback | Да |
| Windsurf | rules | Best effort | Да | Fallback | Да |

## Установка

Требуется Python 3.10 или новее.

### Таблица команд

| Задача | Linux / macOS | Windows PowerShell | Примечание |
|---|---|---|---|
| Установка на английском | `./install.sh` | `py -3 install.py --agents all --auto` | Мастер Bash определяет агентов; Python запускается без вопросов |
| Установка на русском | `./install.sh --ru` | `py -3 install.ru.py --agents all --auto` | Тот же API и те же адаптеры |
| Автоматическая установка | `./install.sh --agents all --auto --yes` | `py -3 install.py --agents all --auto` | Для CI и скриптов |
| Предпросмотр / dry-run | `./install.sh --agents all --dry-run --yes` | `py -3 install.py --agents all --dry-run` | Файлы не изменяются |
| Удаление | `./install.sh --uninstall --yes` | `py -3 install.py --uninstall` | Удаляются только неизменённые управляемые файлы и блоки |
| Проверка | `./verify.sh` | `py -3 tools/selfcheck.py` | Полная самостоятельная проверка проекта |

### Linux, macOS, Git Bash

```bash
chmod +x install.sh
./install.sh
```

Английский язык является основным. Для русского интерактивного мастера:

```bash
./install.sh --ru
```

### Windows PowerShell

```powershell
py -3 install.py
```

Русский entry point в Windows:

```powershell
py -3 install.ru.py
```

Можно также выбрать язык напрямую: `py -3 install.py --lang ru`.

Установщик определяет доступные агенты, позволяет выбрать project/global
область, режим AUTO/PREVIEW/OFF, scope, quality gate, fallback для неизвестных
моделей, backups и dry-run. Повторный запуск безопасен и идемпотентен.
Перед запуском мастера проверяются Python и манифест адаптеров. Мастер
показывает этапы выбора адаптеров, места установки, настроек и подтверждения;
после установки выводится результат. Отмена до записи файлов
завершает работу без изменений.

Для CI используйте автоматический режим с явным набором агентов (`--yes` нужен
только оболочке Bash). В Windows интерактивный мастер доступен через Git Bash;
прямой вызов Python выполняется без вопросов.
`--dry-run` показывает план без записи. Повторная установка не дублирует
управляемые записи и сохраняет пользовательские файлы; при ошибке транзакция
откатывает изменения.

## OpenCode

При включённой native-интеграции устанавливаются server plugin, TUI plugin и
регистрация в `tui.json`.

### Индикатор

- `● PO AUTO` — активен автоматический режим;
- `◐ PO PREVIEW` — режим предварительного просмотра;
- `○ PO OFF` — optimizer отключён;
- `◇ PO GENERIC` — используется нейтральный fallback для неизвестной модели;
- `! PO CONFIG` — конфигурация некорректна, включён безопасный OFF fallback;
- `*` после индикатора — есть session override.

### Настройки через Ctrl+P

Откройте:

```text
Ctrl+P → Prompt Optimizer · Settings
```

Доступны параметры:

- **Behavior** — Auto, Preview или Off;
- **Scope** — первый запрос или все запросы;
- **Quality gate** — Adaptive, Pass, Light или Full;
- **Unsupported model** — Skip или Generic fallback;
- **Save to** — Session, Project или Global.

Расположение конфигурации:

- Project: `.opencode/prompt-optimizer.json`;
- Global: `~/.config/opencode/prompt-optimizer.json`;
- Session: `~/.config/opencode/prompt-optimizer-sessions/`.

Быстрый shortcut `Ctrl+Shift+P` также открывает настройки. Slash-команды
остаются доступны:

```text
/prompt-optimizer status
/prompt-optimizer explain
/prompt-optimizer on|off|preview|first|all|pass|light|full|adaptive|reset
```

### Пример OpenCode-конфигурации

```json
{
  "schemaVersion": 1,
  "behavior": "auto",
  "scope": "all",
  "qualityGate": "adaptive",
  "unsupportedModel": "skip"
}
```

`qualityGate` также поддерживает `pass`, `light`, `full` и legacy boolean.
В OpenCode v1 PREVIEW является advisory: plugin не может отменить выполнение
через host-level mutation barrier, поэтому окончательное подтверждение зависит
от возможностей активной модели и TUI.

## Режимы

- **AUTO** — оптимизировать только когда это повышает качество выполнения и
  сразу продолжать в том же model turn;
- **PREVIEW** — показать или запросить подтверждение оптимизированного потока,
  если host предоставляет соответствующий механизм;
- **OFF** — оставить интеграцию установленной, но отключить автоматическую
  оптимизацию.

`scope: "first"` ограничивает автоматическую обработку первым пользовательским
запросом сессии.

## Неизвестные модели

По умолчанию неизвестные или недоступные модели используют нейтральный
structured fallback либо пропускаются согласно `unsupportedModel`. Проект не
угадывает vendor-specific профиль по неполному имени модели.

## Проверки разработчика

```bash
npm install
npm run verify
npm run verify:bash
npm test
npm run verify:ts
npm run test:runtime
python -B evals/run.py
```

## Документация

- [English README](README.md)
- [Changelog](CHANGELOG.md)
- [Compatibility matrix](COMPATIBILITY.md)
- [Configuration decision guide](DECISION-GUIDE.md)
- [Testing guide](TESTING.md)
- [OpenCode adapter](adapters/opencode/README.md)
