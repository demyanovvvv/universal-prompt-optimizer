# Universal Prompt Optimizer v5.12

**Язык:** Русский · [English README](README.md)

**Быстрые ссылки:** [Установка](#установка) · [Команды](#универсальные-команды) · [OpenCode](#opencode) · [Совместимость](COMPATIBILITY.md) · [Выбор конфигурации](DECISION-GUIDE.md) · [История изменений](CHANGELOG.md)

Оптимизация запросов с учётом активной модели для восьми coding-агентов.
Напишите обычный запрос: агент применит только полезные рекомендации для
фактической модели, сохранит смысл и ограничения и выполнит задачу в том же
обращении к модели.

Цель — повысить качество выполнения с первой попытки, уменьшить ошибки в
границах задачи, число исправлений и суммарный расход токенов. Отдельный
LLM-вызов для переписывания запроса не требуется.

## Основные возможности

- **Адаптивная обработка:** PASS сохраняет точный запрос кратким, LIGHT
  добавляет недостающую границу, FULL формирует краткое описание сложной задачи.
- **Точная маршрутизация:** 26 внутренних профилей для OpenAI, Claude, DeepSeek,
  GLM, Gemini и других моделей. Неизвестные или неоднозначные ID используют
  выбранную политику `generic` или `skip` без угадывания варианта модели.
- **AUTO / PREVIEW / OFF:** автоматическая адаптация, предварительный просмотр
  или отключённая оптимизация. Гарантии подтверждения зависят от агента;
  в OpenCode v1 PREVIEW остаётся рекомендательным.
- **Управление OpenCode:** компактный индикатор, меню в стандартной палитре
  команд с текущими значениями и сохранение настроек для сессии, проекта или глобально.
- **Локальная работа:** нет телеметрии и скрытых сетевых вызовов; текст запросов
  не сохраняется как метрики. Разрешения агента и ограничения пользователя соблюдаются.
- **Повторяемая установка:** проектная и глобальная установка, атомарная запись,
  откат при ошибке, диагностика без изменений и очистка штатных старых модельных
  команд с сохранением пользовательских инструкций.

## Поддерживаемые агенты

| Агент | Интеграция | Точная маршрутизация модели | AUTO | PREVIEW | OFF |
|---|---|---:|---:|---:|---:|
| OpenCode | native server plugin + TUI | Да | Native | Advisory | Да |
| Pi | native extension | Да | Native | Native | Да |
| Cursor | hooks + rule | Да, если модель передана runtime | Да | Question/fallback | Да |
| Gemini CLI | hooks + `GEMINI.md` | Точная после BeforeModel; явная модель до первого вызова | Да | `ask_user`/fallback | Да |
| Claude Code | skill + `CLAUDE.md` | Семейство Claude | Да | Question/fallback | Да |
| GitHub Copilot CLI | instructions | Best effort | Да | Interactive/fallback | Да |
| OpenAI Codex | `AGENTS.md` | Best effort | Да | Fallback | Да |
| Windsurf | rules | Best effort | Да | Fallback | Да |

## Поддерживаемые модели

| Семейство | Профили |
|---|---|
| OpenAI | GPT-6 Astra, GPT-6.1 Sol, GPT-6 Sol, GPT-6 Luna, GPT-5.6 Terra, GPT-5.6 Sol, GPT-5.6 Luna |
| Claude | Fable 5.1, Fable 5, Opus 5.5, Opus 5, Opus 4.8, Sonnet 5.5, Sonnet 5 |
| GLM | GLM-5.2, GLM-5.3, GLM-5.3-Flash |
| DeepSeek | V4.1 Flash, V4 Flash, V4 Pro |
| Другие | Kimi K3, Muse Spark 1.3, Hy4-preview, Qwen3.8-Max, Gemini 3.8 Flash, Grok 4.6 |

Профиль выбирается по точному ID активной модели, если агент его предоставляет.
Поддерживаемые aliases перечислены во внутреннем [реестре моделей](.agents/skills/prompt-optimizer/references/model-registry.json).
Неоднозначный `deepseek-v4` не выбирает вариант автоматически.

## Универсальные команды

| Команда | Назначение |
|---|---|
| `/prompt <задача>` | Определить активную модель, оптимизировать запрос и выполнить задачу. |
| `/prompt-only <задача>` | Вернуть только готовый оптимизированный промпт. |
| `/prompt-optimizer` | Посмотреть или изменить настройки оптимизатора. |

OpenCode устанавливает только эти три универсальных файла команд. Native TUI
также предоставляет `/po` и `/po-status`. Отдельные команды для Opus, Fable и
других моделей не нужны: профили выбираются внутри оптимизатора.
Повторите установку в той же области, чтобы удалить штатные устаревшие команды,
затем перезапустите OpenCode. Изменённые пользователем и сторонние команды сохраняются.

## Установка

Требуется Python 3.10 или новее.

### Таблица команд

| Задача | Linux / macOS | Windows PowerShell | Примечание |
|---|---|---|---|
| Установка на английском | `./install.sh` | `py -3 install.py --agents all --auto` | Мастер Bash определяет агентов; Python запускается без вопросов |
| Установка на русском | `./install.sh --ru` | `py -3 install.ru.py --agents all --auto` | Тот же API и те же адаптеры |
| Автоматическая установка | `./install.sh --agents all --auto --yes` | `py -3 install.py --agents all --auto` | Для CI и скриптов |
| Предпросмотр / dry-run | `./install.sh --agents all --dry-run --yes` | `py -3 install.py --agents all --dry-run` | Файлы не изменяются |
| Удаление | `./install.sh --uninstall --yes` | `py -3 install.py --uninstall` | Удаляются управляемые файлы, резервные копии и блоки |
| Проверка | `./verify.sh` | `py -3 tools/selfcheck.py` | Полная самостоятельная проверка проекта |

Повторный запуск установки обновляет управляемые файлы до текущей версии пакета.
Удаление убирает файлы установщика даже после изменения их содержимого, а также
его резервные копии. Пользовательский текст вне управляемых блоков, сторонние
hooks и дополнительные поля общих JSON-конфигураций сохраняются.

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
Ctrl+P → command palette → Prompt Optimizer
```

Группа содержит меню, настройки и статус. Каждая строка меню показывает текущее
значение настройки в подзаголовке. Для быстрого открытия настроек используйте
`Ctrl+Shift+P` или `/po`.

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

Slash-команды остаются доступны. `/po-status` открывает native TUI-диалог со
статусом; серверное управление поддерживает:

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

`qualityGate` в общей и OpenCode-конфигурации сохраняет выбранное значение
`adaptive`, `pass`, `light` или `full`; legacy boolean также принимается.
Инструкционные адаптеры читают актуальный проектный конфиг, затем глобальный;
значения из установленного блока служат резервными. Gemini применяет автоматический
preflight только при непустом сигнале текущего BeforeAgent hook. Глобальный hook
запускает скрипт из домашнего каталога независимо от рабочего проекта.
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

CI проверяет маршрутизацию, совместимость адаптеров, установку и удаление,
а также синтетические сценарии prompt injection, разрушительных действий
и сохранения секретов. Полная матрица проверок описана в [TESTING.md](TESTING.md).

```bash
npm install
npm run verify
npm run verify:bash
npm test
npm run verify:ts
npm run test:runtime
npm run check:model-registry
python -B evals/run.py
```

## Документация

- [English README](README.md)
- [Changelog](CHANGELOG.md)
- [Compatibility matrix](COMPATIBILITY.md)
- [Configuration decision guide](DECISION-GUIDE.md)
- [Testing guide](TESTING.md)
- [OpenCode adapter](adapters/opencode/README.md)
