#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-}"
VERSION="$(tr -d '\r\n' < "$SCRIPT_DIR/VERSION")"


scope="project"
scope_explicit=0
project="."
agents_arg=""
agent_selection_mode=""  # auto | detected | all | manual | cli
detect_requested=0
list_requested=0
interactive=0
auto_integration=1
integration_explicit=0
settings_cli=()
behavior="auto"
prompt_scope="all"
quality_gate="on"
unsupported_model="skip"
backup="on"
dry_run=0
assume_yes=0
doctor_mode=0
uninstall_mode=0
UI_LANG="en"

is_tty() { [[ -t 0 && -t 1 ]]; }
command_exists() { command -v "$1" >/dev/null 2>&1; }
python_works() { [[ -n "$1" ]] && command_exists "$1" && "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; }
resolve_python() {
  if [[ -n "${PYTHON_BIN:-}" ]] && python_works "$PYTHON_BIN"; then return 0; fi
  for candidate in python3 python py; do
    if python_works "$candidate"; then PYTHON_BIN="$candidate"; return 0; fi
  done
  return 1
}
load_agent_ids() {
  local candidate output id label
  for candidate in "${PYTHON_BIN:-}" python3 python py; do
    [[ -n "$candidate" ]] || continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    output=$("$candidate" -B -c 'import json,sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,str(root)); from installer.detection import AGENT_NAMES; print("\n".join(agent + "\t" + AGENT_NAMES[agent] for agent in json.loads((root / "adapters/manifest.json").read_text(encoding="utf-8"))["adapters"]))' "$SCRIPT_DIR") || continue
    AGENT_IDS=(); AGENT_NAMES=()
    while IFS=$'\t' read -r id label; do
      [[ -n "$id" ]] && { AGENT_IDS+=("$id"); AGENT_NAMES+=("$label"); }
    done <<< "$output"
    ((${#AGENT_IDS[@]} > 0)) && return 0
  done
  return 1
}
AGENT_IDS=()
AGENT_NAMES=()
DETECTED_IDS=()
DETECTED_REASONS=()
DETECTION_READY=0
load_agent_ids || { printf '%s\n' 'Python 3 is required to read adapters/manifest.json' >&2; exit 1; }
lower() { printf "%s" "$1" | tr "[:upper:]" "[:lower:]"; }

# Language flags are handled before wizard detection so `./install.sh --ru`
# still opens the interactive wizard when it is the only argument.
ORIGINAL_ARGS=("$@")
FILTERED_ARGS=()
i=0
while [[ $i -lt ${#ORIGINAL_ARGS[@]} ]]; do
  arg="${ORIGINAL_ARGS[$i]}"
  case "$arg" in
    ru|--ru|-ru) UI_LANG="ru" ;;
    en|--en|-en) UI_LANG="en" ;;
    --lang)
      i=$((i+1))
      [[ $i -lt ${#ORIGINAL_ARGS[@]} ]] || { echo "Missing value for --lang" >&2; exit 2; }
      case "${ORIGINAL_ARGS[$i]}" in ru|RU) UI_LANG="ru" ;; en|EN) UI_LANG="en" ;; *) echo "Unsupported language: ${ORIGINAL_ARGS[$i]}" >&2; exit 2 ;; esac
      ;;
    --lang=ru|--lang=RU) UI_LANG="ru" ;;
    --lang=en|--lang=EN) UI_LANG="en" ;;
    *) FILTERED_ARGS+=("$arg") ;;
  esac
  i=$((i+1))
done
set -- "${FILTERED_ARGS[@]}"

if is_tty; then
  BOLD='\033[1m'; DIM='\033[2m'; GREEN='\033[32m'; CYAN='\033[36m'; YELLOW='\033[33m'; RED='\033[31m'; RESET='\033[0m'
else
  BOLD=''; DIM=''; GREEN=''; CYAN=''; YELLOW=''; RED=''; RESET=''
fi

tr_ui() {
  local key="$1"
  if [[ "$UI_LANG" == "ru" ]]; then
    case "$key" in
      subtitle) echo "Интерактивный установщик" ;;
      divider) echo "------------------------------------------------------------" ;;
      scope_project) echo "Проект" ;;
      scope_global) echo "Глобально" ;;
      recommended) echo "рекомендуется" ;;
      enter_default) echo "Enter — по умолчанию" ;;
      detected) echo "обнаружен" ;;
      not_detected) echo "не обнаружен" ;;
      command) echo "команда" ;;
      config_dir) echo "каталог конфигурации" ;;
      app_dir) echo "каталог конфигурации/приложения" ;;
      all_agents) echo "Все поддерживаемые агенты" ;;
      none) echo "нет" ;;
      on) echo "ВКЛ" ;;
      off) echo "ВЫКЛ" ;;
      cancelled) echo "Установка отменена." ;;
      choose_1_4) echo "Выберите 1–4." ;;
      choose_1_3) echo "Выберите 1–3." ;;
      select_one) echo "Выберите хотя бы одного агента." ;;
      ignored) echo "Пропущено" ;;
      yn_error) echo "Введите y/n или да/нет." ;;
      *) echo "$key" ;;
    esac
  else
    case "$key" in
      subtitle) echo "Interactive installer" ;;
      divider) echo "------------------------------------------------------------" ;;
      scope_project) echo "Project" ;;
      scope_global) echo "Global" ;;
      recommended) echo "recommended" ;;
      enter_default) echo "Enter = default" ;;
      detected) echo "detected" ;;
      not_detected) echo "not detected" ;;
      command) echo "command" ;;
      config_dir) echo "config directory" ;;
      app_dir) echo "config/application directory" ;;
      all_agents) echo "All supported agents" ;;
      none) echo "none" ;;
      on) echo "ON" ;;
      off) echo "OFF" ;;
      cancelled) echo "Cancelled." ;;
      choose_1_4) echo "Choose 1-4." ;;
      choose_1_3) echo "Choose 1-3." ;;
      select_one) echo "Select at least one agent." ;;
      ignored) echo "Ignored" ;;
      yn_error) echo "Enter y/n." ;;
      *) echo "$key" ;;
    esac
  fi
}

usage() {
  if [[ "$UI_LANG" == "ru" ]]; then
    cat <<TXT
Universal Prompt Optimizer v${VERSION} — установщик

Рекомендуемая интерактивная установка:
  ./install.sh --ru
  ./install.sh ru

Мастер автоматически определяет установленных агентов, показывает найденных
агентов уже выбранными, позволяет установить их одним Enter, выбрать ВСЕХ
поддерживаемых агентов или вручную отметить любое сочетание. Все настройки
доступны прямо внутри мастера; флаги нужны только для автоматизации/CI.

Обновление: запустите установщик из папки нового релиза в той же области и проекте.
Без мастера настройки сохраняются; глобально найденные агенты добавляются к ранее установленным.
Если ни одного агента не обнаружено и не записано, файлы не устанавливаются.

Необязательные флаги:
  ru, --ru, -ru          Русский интерфейс
  en, --en, -en          Английский интерфейс
  --lang ru|en           Язык интерфейса
  --detect-agents        Автоопределение агентов без мастера
  --agents all|opencode,cursor,deepseek-harness,...
  --scope project|global
  --project PATH
  --auto | --no-auto
  --behavior auto|preview|off
  --prompt-scope all|first
  --quality-gate on|off|pass|light|full|adaptive
  --unsupported-model skip|generic
  --python-bin PATH|COMMAND
  --backup | --no-backup
  --dry-run
  --doctor, --status       Только проверить состояние установки
  --uninstall              Безопасно удалить управляемые файлы/блоки
  -y, --yes
  --list-agents
  -h, --help
TXT
  else
    cat <<TXT
Universal Prompt Optimizer v${VERSION} installer

Recommended interactive installation:
  ./install.sh

Russian interface:
  ./install.sh --ru
  ./install.sh ru

The interactive wizard auto-detects installed agents, lets you install the detected
set with one Enter, choose all supported agents, or select any combination manually.
Every installer setting is configurable inside the wizard; CLI flags are optional and
are kept only for automation/CI.

Update: rerun the installer from the new release folder in the same scope and target.
Non-wizard updates preserve settings; global installs add detected agents to recorded adapters.
If no agents are detected or recorded, no files are installed.

Optional flags:
  ru, --ru, -ru
  en, --en, -en
  --lang ru|en
  --detect-agents
  --agents all|opencode,cursor,deepseek-harness,...
  --scope project|global
  --project PATH
  --auto | --no-auto
  --behavior auto|preview|off
  --prompt-scope all|first
  --quality-gate on|off|pass|light|full|adaptive
  --unsupported-model skip|generic
  --python-bin PATH|COMMAND
  --backup | --no-backup
  --dry-run
  --doctor, --status
  --uninstall
  -y, --yes
  --list-agents
  -h, --help
TXT
  fi
}

header() {
  printf '\n%bUniversal Prompt Optimizer v%s%b\n' "$BOLD" "$VERSION" "$RESET"
  printf '%b%s%b\n\n' "$CYAN" "$(tr_ui subtitle)" "$RESET"
}

section() {
  printf '\n%b%s%b\n' "$BOLD" "$1" "$RESET"
  printf '%b%s%b\n' "$DIM" "$(tr_ui divider)" "$RESET"
}

refresh_agent_detection() {
  local output id reason
  resolve_python || return 1
  output=$("$PYTHON_BIN" -B -c 'import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from installer.detection import detect_agents; project=Path(sys.argv[3]).expanduser() if sys.argv[2] == "project" else None; print("\n".join(agent + "\t" + reason for agent,reason in detect_agents(Path.home(), project=project).items()))' "$SCRIPT_DIR" "$scope" "$project") || return 1
  DETECTED_IDS=(); DETECTED_REASONS=()
  while IFS=$'\t' read -r id reason; do
    [[ -n "$id" ]] && { DETECTED_IDS+=("$id"); DETECTED_REASONS+=("$reason"); }
  done <<< "$output"
  DETECTION_READY=1
}

agent_detect_reason() {
  local id="$1" i reason
  for i in "${!DETECTED_IDS[@]}"; do
    [[ "$id" == "${DETECTED_IDS[$i]}" ]] || continue
    reason="${DETECTED_REASONS[$i]}"
    case "$reason" in
      "command: "*) printf '%s: %s\n' "$(tr_ui command)" "${reason#command: }" ;;
      "config directory") printf '%s\n' "$(tr_ui config_dir)" ;;
      "config/application directory") printf '%s\n' "$(tr_ui app_dir)" ;;
      *) printf '%s\n' "$reason" ;;
    esac
    return 0
  done
  return 1
}

detected_agents_csv() {
  [[ $DETECTION_READY -eq 1 ]] || refresh_agent_detection || return 1
  local found=() id
  for id in "${AGENT_IDS[@]}"; do agent_detect_reason "$id" >/dev/null 2>&1 && found+=("$id"); done
  local IFS=,; echo "${found[*]}"
}

csv_agent_names() {
  local csv="$1" out=() id i
  if [[ "$csv" == "auto" ]]; then
    if [[ "$UI_LANG" == "ru" ]]; then printf '%s' 'Автоопределение + ранее установленные адаптеры'; else printf '%s' 'Auto-detected + previously installed adapters'; fi
    return
  fi
  if [[ "$csv" == "all" ]]; then
    if [[ "$UI_LANG" == "ru" ]]; then printf 'Все поддерживаемые агенты (%d)' "${#AGENT_IDS[@]}"; else printf 'All supported agents (%d)' "${#AGENT_IDS[@]}"; fi
    return
  fi
  local oldifs="$IFS"; IFS=','; read -r -a ids <<< "$csv"; IFS="$oldifs"
  for id in "${ids[@]}"; do
    for i in "${!AGENT_IDS[@]}"; do [[ "$id" == "${AGENT_IDS[$i]}" ]] && { out+=("${AGENT_NAMES[$i]}"); break; }; done
  done
  [[ "${#out[@]}" -eq 0 ]] && { printf '%s' "$(tr_ui none)"; return; }
  local result="" name
  for name in "${out[@]}"; do [[ -n "$result" ]] && result+=", "; result+="$name"; done
  printf '%s' "$result"
}

print_agent_status() {
  [[ $DETECTION_READY -eq 1 ]] || refresh_agent_detection || return 1
  local i id reason
  for i in "${!AGENT_IDS[@]}"; do
    id="${AGENT_IDS[$i]}"
    if reason="$(agent_detect_reason "$id" 2>/dev/null)"; then
      printf '  %b[x]%b %-22s %b%s%b  %s\n' "$GREEN" "$RESET" "${AGENT_NAMES[$i]}" "$GREEN" "$(tr_ui detected)" "$RESET" "$reason"
    else
      printf '  [ ] %-22s %b%s%b\n' "${AGENT_NAMES[$i]}" "$DIM" "$(tr_ui not_detected)" "$RESET"
    fi
  done
}

read_value() {
  local prompt="$1" default="$2" value
  read -r -p "$prompt [$default]: " value || true
  REPLY="${value:-$default}"
}

read_yes_no() {
  local prompt="$1" default="$2" value suffix
  [[ "$default" == "yes" ]] && suffix="Y/n" || suffix="y/N"
  while true; do
    read -r -p "$prompt [$suffix]: " value || true
    value="${value:-$default}"
    case "$(lower "$value")" in
      y|yes|да|д) YESNO=yes; return 0 ;;
      n|no|нет|н) YESNO=no; return 0 ;;
      *) echo "$(tr_ui yn_error)" ;;
    esac
  done
}

manual_agent_selector() {
  [[ $DETECTION_READY -eq 1 ]] || refresh_agent_detection || return 1
  local -a selected=()
  local i input token
  for i in "${!AGENT_IDS[@]}"; do selected[$i]=0; done
  for i in "${!AGENT_IDS[@]}"; do agent_detect_reason "${AGENT_IDS[$i]}" >/dev/null 2>&1 && selected[$i]=1; done
  while true; do
    if [[ "$UI_LANG" == "ru" ]]; then
      section "Ручной выбор агентов"
      echo "Обнаруженные агенты уже отмечены. Переключите нужные пункты."
    else
      section "Manual agent selection"
      echo "Detected agents are preselected. Toggle any entries you want to add/remove."
    fi
    echo
    for i in "${!AGENT_IDS[@]}"; do
      if [[ "${selected[$i]}" -eq 1 ]]; then printf '  %d) %b[x]%b %s\n' "$((i+1))" "$GREEN" "$RESET" "${AGENT_NAMES[$i]}"; else printf '  %d) [ ] %s\n' "$((i+1))" "${AGENT_NAMES[$i]}"; fi
    done
    echo
    if [[ "$UI_LANG" == "ru" ]]; then
      echo "  a) Выбрать ВСЕХ"
      echo "  n) Снять выбор со всех"
      echo "  d) Вернуть автоматически обнаруженных"
      echo "  Enter) Продолжить с отмеченными агентами"
    else
      echo "  a) Select ALL"
      echo "  n) Clear ALL"
      echo "  d) Reset to auto-detected"
      echo "  Enter) Continue with checked agents"
    fi
    read -r -p "> " input || true
    [[ -z "$input" ]] && break
    input="${input//,/ }"
    for token in $input; do
      case "$(lower "$token")" in
        a|все) for i in "${!selected[@]}"; do selected[$i]=1; done ;;
        n|none|нет) for i in "${!selected[@]}"; do selected[$i]=0; done ;;
        d|detect|авто)
          refresh_agent_detection || return 1
          for i in "${!selected[@]}"; do selected[$i]=0; agent_detect_reason "${AGENT_IDS[$i]}" >/dev/null 2>&1 && selected[$i]=1; done
          ;;
        ''|*[!0-9]*) echo "$(tr_ui ignored): $token" ;;
        *)
          i=$((10#$token - 1))  # base-10 so '08' is not parsed as octal
          [[ "$i" -ge 0 && "$i" -lt "${#AGENT_IDS[@]}" ]] || { echo "$(tr_ui ignored): $token"; continue; }
          [[ "${selected[$i]}" -eq 1 ]] && selected[$i]=0 || selected[$i]=1
          ;;
      esac
    done
  done
  local out=()
  for i in "${!AGENT_IDS[@]}"; do [[ "${selected[$i]}" -eq 1 ]] && out+=("${AGENT_IDS[$i]}"); done
  [[ "${#out[@]}" -eq 0 ]] && return 1
  local IFS=,; agents_arg="${out[*]}"; agent_selection_mode="manual"; return 0
}

choose_agents_interactive() {
  local detected choice
  while true; do
    refresh_agent_detection || return 1
    if [[ "$UI_LANG" == "ru" ]]; then
      section "1/4  Автоопределение агентов"
      echo "Установщик автоматически проверяет команды и известные каталоги конфигурации/приложений."
    else
      section "1/4  Agent auto-detection"
      echo "The installer scans commands and known configuration/application directories automatically."
    fi
    echo; print_agent_status; detected="$(detected_agents_csv)"; echo
    if [[ -n "$detected" ]]; then
      if [[ "$UI_LANG" == "ru" ]]; then
        printf '%bНайдено:%b %s\n\n' "$GREEN" "$RESET" "$(csv_agent_names "$detected")"
        printf '%b\n' "  1) Установить для найденных агентов  ${DIM}[рекомендуется / Enter]${RESET}"
        echo "  2) Установить для ВСЕХ поддерживаемых агентов"
        echo "  3) Выбрать агентов вручную (несколько сразу)"
        echo "  4) Повторить сканирование"
        echo "  q) Отмена"
      else
        printf '%bFound:%b %s\n\n' "$GREEN" "$RESET" "$(csv_agent_names "$detected")"
        printf '%b\n' "  1) Install for detected agents  ${DIM}[recommended / Enter]${RESET}"
        echo "  2) Install for ALL supported agents"
        echo "  3) Choose agents manually (multi-select)"
        echo "  4) Re-scan"
        echo "  q) Cancel"
      fi
      read -r -p "> " choice || true; choice="${choice:-1}"
      case "$(lower "$choice")" in
        1|detected|auto|авто|найденные) agents_arg="$detected"; agent_selection_mode="detected"; return 0 ;;
        2|all|все) agents_arg="all"; agent_selection_mode="all"; return 0 ;;
        3|manual|вручную) manual_agent_selector && return 0 || echo "$(tr_ui select_one)" ;;
        4|rescan|r|скан) continue ;;
        q|quit|выход) echo "$(tr_ui cancelled)"; exit 0 ;;
        *) echo "$(tr_ui choose_1_4)" ;;
      esac
    else
      if [[ "$UI_LANG" == "ru" ]]; then
        printf '%bПоддерживаемые агенты автоматически не обнаружены.%b\n' "$YELLOW" "$RESET"
        echo "Можно установить адаптеры для агентов, которые вы планируете использовать."
        echo
        printf '%b\n' "  1) Выбрать агентов вручную  ${DIM}[рекомендуется / Enter]${RESET}"
        echo "  2) Установить для ВСЕХ поддерживаемых агентов"
        echo "  3) Повторить сканирование"
        echo "  q) Отмена"
      else
        printf '%bNo supported agents were detected automatically.%b\n' "$YELLOW" "$RESET"
        echo "You can still install adapters for any agent you plan to use."
        echo
        printf '%b\n' "  1) Choose agents manually  ${DIM}[recommended / Enter]${RESET}"
        echo "  2) Install for ALL supported agents"
        echo "  3) Re-scan"
        echo "  q) Cancel"
      fi
      read -r -p "> " choice || true; choice="${choice:-1}"
      case "$(lower "$choice")" in
        1|manual|вручную) manual_agent_selector && return 0 || echo "$(tr_ui select_one)" ;;
        2|all|все) agents_arg="all"; agent_selection_mode="all"; return 0 ;;
        3|rescan|r|скан) continue ;;
        q|quit|выход) echo "$(tr_ui cancelled)"; exit 0 ;;
        *) echo "$(tr_ui choose_1_3)" ;;
      esac
    fi
  done
}

configure_scope_interactive() {
  local choice
  if [[ "$UI_LANG" == "ru" ]]; then
    section "2/4  Место установки"
    printf '%b\n' "  1) Локально — в проект  ${DIM}[рекомендуется]${RESET}"
    echo "  2) Глобально"
  else
    section "2/4  Installation location"
    printf '%b\n' "  1) Local — project  ${DIM}[recommended]${RESET}"
    echo "  2) Global"
  fi
  read -r -p "> " choice || true; choice="${choice:-1}"
  case "$(lower "$choice")" in
    2|global|глобально) scope=global ;;
    q|quit|отмена) echo "$(tr_ui cancelled)"; exit 0 ;;
    1|project|local|локально) scope=project ;;
    *) if [[ "$UI_LANG" == ru ]]; then echo "Выберите 1, 2 или q."; else echo "Choose 1, 2 or q."; fi; configure_scope_interactive; return ;;
  esac
  if [[ "$scope" == "project" ]]; then
    if [[ "$UI_LANG" == "ru" ]]; then read_value "Путь к проекту" "$project"; else read_value "Project path" "$project"; fi
    project="$REPLY"
  fi
  DETECTION_READY=0
  if [[ "$agent_selection_mode" == "detected" ]]; then
    refresh_agent_detection || return 1
    agents_arg="$(detected_agents_csv)"
    print_agent_status
  fi
}

configure_behavior_interactive() {
  local choice
  if [[ "$UI_LANG" == "ru" ]]; then
    section "3/4  Настройки Prompt Optimizer"
    echo "Все параметры настраиваются здесь — флаги командной строки и ручное редактирование JSON не нужны."
    echo
    echo "Автоматическая/нативная интеграция:"
    printf '%b\n' "  1) ВКЛ  - установить hooks/plugins/rules и использовать Prompt Optimizer автоматически ${DIM}[рекомендуется]${RESET}"
    echo "  2) ВЫКЛ - установить только skills/команды, без автоматического preflight"
  else
    section "3/4  Prompt Optimizer settings"
    echo "Everything below can be changed here; no CLI flags or manual JSON editing are required."
    echo
    echo "Automatic/native integration:"
    printf '%b\n' "  1) ON  - install hooks/plugins/rules and use Prompt Optimizer automatically ${DIM}[recommended]${RESET}"
    echo "  2) OFF - install skills/commands only; no automatic preflight"
  fi
  read -r -p "> " choice || true; choice="${choice:-1}"; case "$choice" in 2) auto_integration=0 ;; *) auto_integration=1 ;; esac

  if [[ $auto_integration -eq 1 ]]; then
    echo
    if [[ "$UI_LANG" == "ru" ]]; then
      echo "Автоматический режим:"
      printf '%b\n' "  1) AUTO        - при необходимости незаметно оптимизировать промпт и сразу выполнить ${DIM}[рекомендуется]${RESET}"
      echo "  2) PREVIEW     - сначала показать оптимизированный промпт и запросить подтверждение"
      echo "  3) OFF         - оставить адаптер установленным, но отключить автооптимизацию"
    else
      echo "Automatic behavior:"
      printf '%b\n' "  1) AUTO    - optimize silently when useful, then execute ${DIM}[recommended]${RESET}"
      echo "  2) PREVIEW - show optimized prompt first and ask for confirmation"
      echo "  3) OFF     - keep adapter installed but disable automatic optimization"
    fi
    read -r -p "> " choice || true; choice="${choice:-1}"; case "$choice" in 2) behavior=preview ;; 3) behavior=off ;; *) behavior=auto ;; esac

    echo
    if [[ "$UI_LANG" == "ru" ]]; then
      echo "Какие пользовательские запросы обрабатывать?"
      printf '%b\n' "  1) ВСЕ запросы ${DIM}[рекомендуется; quality gate не даёт лишний раз переписывать хороший промпт]${RESET}"
      echo "  2) Только ПЕРВЫЙ пользовательский запрос в каждой сессии"
    else
      echo "Which user turns should be eligible?"
      printf '%b\n' "  1) ALL user turns ${DIM}[recommended; quality gate prevents needless rewrites]${RESET}"
      echo "  2) FIRST user turn in each session only"
    fi
    read -r -p "> " choice || true; choice="${choice:-1}"; case "$choice" in 2) prompt_scope=first ;; *) prompt_scope=all ;; esac

    echo
    if [[ "$UI_LANG" == "ru" ]]; then
      echo "Quality Gate:"
      printf '%b\n' "  1) АДАПТИВНЫЙ - PASS для точных, LIGHT для неполных, FULL для сложных ${DIM}[рекомендуется]${RESET}"
      echo "  2) PASS - пропускать точные запросы без нормализации"
      echo "  3) LIGHT - только легкая нормализация"
      echo "  4) FULL - полная нормализация каждого запроса"
    else
      echo "Quality gate:"
      printf '%b\n' "  1) ADAPTIVE - PASS precise, LIGHT incomplete, FULL complex ${DIM}[recommended]${RESET}"
      echo "  2) PASS - skip precise requests without normalization"
      echo "  3) LIGHT - light normalization only"
      echo "  4) FULL - full normalization for every request"
    fi
    read -r -p "> " choice || true; choice="${choice:-1}"; case "$choice" in 2) quality_gate=pass ;; 3) quality_gate=light ;; 4) quality_gate=full ;; *) quality_gate=adaptive ;; esac

    echo
    if [[ "$UI_LANG" == "ru" ]]; then
      echo "Если активная модель неизвестна или не поддерживается:"
      printf '%b\n' "  1) SKIP    - не угадывать model-specific профиль ${DIM}[рекомендуется / безопаснее]${RESET}"
      echo "  2) GENERIC - использовать нейтральный model-agnostic профиль"
    else
      echo "If the active model is unknown/unsupported:"
      printf '%b\n' "  1) SKIP    - do not guess a model-specific profile ${DIM}[recommended / safest]${RESET}"
      echo "  2) GENERIC - use the neutral model-agnostic optimizer profile"
    fi
    read -r -p "> " choice || true; choice="${choice:-1}"; case "$choice" in 2) unsupported_model=generic ;; *) unsupported_model=skip ;; esac
  fi

  echo
  if [[ "$UI_LANG" == "ru" ]]; then
    echo "Резервные копии существующих правил/конфигурации:"
    printf '%b\n' "  1) ВКЛ  ${DIM}[рекомендуется]${RESET}"
    echo "  2) ВЫКЛ"
  else
    echo "Backups of existing rules/configuration:"
    printf '%b\n' "  1) ON  ${DIM}[recommended]${RESET}"
    echo "  2) OFF"
  fi
  read -r -p "> " choice || true; choice="${choice:-1}"; case "$choice" in 2) backup=off ;; *) backup=on ;; esac

  echo
  if [[ "$UI_LANG" == "ru" ]]; then
    echo "Режим установки:"
    printf '%b\n' "  1) ЗАПИСАТЬ изменения ${DIM}[рекомендуется]${RESET}"
    echo "  2) DRY RUN - только показать изменения, не записывая файлы"
  else
    echo "Installation mode:"
    printf '%b\n' "  1) WRITE changes normally ${DIM}[recommended]${RESET}"
    echo "  2) DRY RUN - show what would change without writing files"
  fi
  read -r -p "> " choice || true; choice="${choice:-1}"; case "$choice" in 2) dry_run=1 ;; *) dry_run=0 ;; esac
}

show_summary() {
  if [[ "$UI_LANG" == "ru" ]]; then section "4/4  Проверка настроек"; else section "4/4  Review"; fi
  if [[ "$UI_LANG" == "ru" ]]; then
    printf '  %-28s %s\n' "Область установки:" "$([[ "$scope" == project ]] && echo "проект" || echo "глобально")"
    [[ "$scope" == "project" ]] && printf '  %-28s %s\n' "Путь к проекту:" "$project"
    printf '  %-28s %s\n' "Агенты:" "$(csv_agent_names "$agents_arg")"
    printf '  %-28s %s\n' "Автоматическая интеграция:" "$([[ $auto_integration -eq 1 ]] && echo ВКЛ || echo ВЫКЛ)"
    if [[ $auto_integration -eq 1 ]]; then
      local b_ru s_ru q_ru u_ru
      case "$behavior" in auto) b_ru="AUTO" ;; preview) b_ru="PREVIEW" ;; off) b_ru="OFF" ;; esac
      [[ "$prompt_scope" == all ]] && s_ru="все запросы" || s_ru="только первый"
      case "$quality_gate" in
        on|adaptive) q_ru="ADAPTIVE" ;;
        off|pass) q_ru="PASS" ;;
        light) q_ru="LIGHT" ;;
        full) q_ru="FULL" ;;
      esac
      [[ "$unsupported_model" == skip ]] && u_ru="SKIP" || u_ru="GENERIC"
      printf '  %-28s %s\n' "Режим:" "$b_ru"
      printf '  %-28s %s\n' "Обрабатываемые запросы:" "$s_ru"
      printf '  %-28s %s\n' "Quality Gate:" "$q_ru"
      printf '  %-28s %s\n' "Неизвестная модель:" "$u_ru"
    fi
    printf '  %-28s %s\n' "Резервные копии:" "$([[ "$backup" == on ]] && echo ВКЛ || echo ВЫКЛ)"
    printf '  %-28s %s\n' "Dry run:" "$([[ $dry_run -eq 1 ]] && echo ВКЛ || echo ВЫКЛ)"
  else
    printf '  %-24s %s\n' "Installation scope:" "$scope"
    [[ "$scope" == "project" ]] && printf '  %-24s %s\n' "Project path:" "$project"
    printf '  %-24s %s\n' "Agents:" "$(csv_agent_names "$agents_arg")"
    printf '  %-24s %s\n' "Automatic integration:" "$([[ $auto_integration -eq 1 ]] && echo ON || echo OFF)"
    if [[ $auto_integration -eq 1 ]]; then
      printf '  %-24s %s\n' "Behavior:" "$(printf '%s' "$behavior" | tr '[:lower:]' '[:upper:]')"
      printf '  %-24s %s\n' "Prompt scope:" "$prompt_scope"
      printf '  %-24s %s\n' "Quality gate:" "$quality_gate"
      printf '  %-24s %s\n' "Unknown model:" "$unsupported_model"
    fi
    printf '  %-24s %s\n' "Backups:" "$backup"
    printf '  %-24s %s\n' "Dry run:" "$([[ $dry_run -eq 1 ]] && echo ON || echo OFF)"
  fi

  # Surface adapter limitations before installation instead of hiding them in README.
  if [[ $auto_integration -eq 1 ]]; then
    local selected_csv=",${agents_arg},"
    [[ "$agents_arg" == "all" ]] && selected_csv=",opencode,codex,cursor,pi,omp,claude,gemini,copilot,windsurf,deepseek-harness,"
    if [[ "$behavior" == "preview" && "$selected_csv" =~ ,(codex|copilot|windsurf), ]]; then
      if [[ "$UI_LANG" == "ru" ]]; then
        printf '\n%bПримечание:%b для Codex/Copilot/Windsurf PREVIEW зависит от доступного UI агента и может работать как текстовый preview + явное подтверждение.\n' "$YELLOW" "$RESET"
      else
        printf '\n%bNote:%b for Codex/Copilot/Windsurf, PREVIEW depends on the agent UI and may fall back to text preview + explicit confirmation.\n' "$YELLOW" "$RESET"
      fi
    fi
    if [[ "$prompt_scope" == "first" && "$selected_csv" =~ ,(codex|claude|copilot|windsurf), ]]; then
      if [[ "$UI_LANG" == "ru" ]]; then
        printf '%bПримечание:%b точный FIRST-turn state гарантирован нативными адаптерами OpenCode/Pi/OMP/Cursor/Gemini CLI; для статических rule-based адаптеров это best-effort.\n' "$YELLOW" "$RESET"
      else
        printf '%bNote:%b exact FIRST-turn state is guaranteed by OpenCode/Pi/OMP/Cursor/Gemini CLI native adapters; static rule-based adapters are best-effort.\n' "$YELLOW" "$RESET"
      fi
    fi
    if [[ "$scope" == "global" && "$selected_csv" == *",cursor,"* ]]; then
      if [[ "$UI_LANG" == "ru" ]]; then
        printf '%bПримечание:%b глобальный Cursor hook/rule автоматически не ставится; для Cursor используйте project scope.\n' "$YELLOW" "$RESET"
      else
        printf '%bNote:%b global Cursor hook/rule is not installed automatically; use project scope for Cursor.\n' "$YELLOW" "$RESET"
      fi
    fi
    if [[ "$selected_csv" == *",gemini,"* && "$unsupported_model" == "skip" ]]; then
      if [[ "$UI_LANG" == "ru" ]]; then
        printf '%bПримечание:%b Gemini CLI не раскрывает resolved model в BeforeAgent. Если GEMINI_MODEL/model.name не заданы точным ID, первый запрос с SKIP пройдёт без model-specific preflight; BeforeModel запомнит точную модель для следующих запросов. Для нейтрального preflight уже на первом ходе выберите GENERIC.\n' "$YELLOW" "$RESET"
      else
        printf '%bNote:%b Gemini CLI does not expose the resolved model in BeforeAgent. If GEMINI_MODEL/model.name is not an exact ID, the first turn with SKIP passes without model-specific preflight; BeforeModel records the exact model for later turns. Choose GENERIC for a neutral first-turn preflight.\n' "$YELLOW" "$RESET"
      fi
    fi
  fi
  if [[ $auto_integration -eq 1 && ( "${agents_arg}" == "all" || ",${agents_arg}," == *",deepseek-harness,"* ) ]]; then
    local overlay_root="$project"
    if [[ "$scope" == "global" ]]; then
      resolve_python || return 1
      overlay_root=$("$PYTHON_BIN" -B -c 'from pathlib import Path; print(Path.home().as_posix())') || return 1
    fi
    local overlay="$overlay_root/.dsh/prompt-optimizer.patch.yml"
    # %q quotes the path safely for the current shell (spaces, apostrophes).
    local command
    printf -v command 'dsh --profile web --patch %q' "$overlay"
    if [[ "$UI_LANG" == "ru" ]]; then
      printf '%bАктивация DeepSeek Harness:%b %s (укажите --patch до аргументов приложения; профиль и cordis.patch.yml не изменяются).\n' "$CYAN" "$RESET" "$command"
    else
      printf '%bDeepSeek Harness activation:%b %s (place --patch before the app arguments; your profile and cordis.patch.yml are never modified).\n' "$CYAN" "$RESET" "$command"
    fi
  fi
}

interactive_wizard() {
  header
  choose_agents_interactive
  configure_scope_interactive
  configure_behavior_interactive
  local choice
  while true; do
    show_summary; echo
    if [[ "$UI_LANG" == "ru" ]]; then
      echo "  Enter) Установить с этими настройками"
      echo "  1) Изменить агентов / повторить автоопределение"
      echo "  2) Изменить настройки Prompt Optimizer"
      echo "  3) Изменить место установки (project/global)"
      echo "  q) Отмена"
    else
      echo "  Enter) Install with these settings"
      echo "  1) Change agents / re-run auto-detect"
      echo "  2) Change Prompt Optimizer settings"
      echo "  3) Change project/global location"
      echo "  q) Cancel"
    fi
    read -r -p "> " choice || true
    case "$(lower "$choice")" in
      "") return 0 ;;
      1|agents|агенты) choose_agents_interactive ;;
      2|settings|настройки) configure_behavior_interactive ;;
      3|location|scope|место) configure_scope_interactive; choose_agents_interactive ;;
      q|quit|выход) echo "$(tr_ui cancelled)"; exit 0 ;;
      *) if [[ "$UI_LANG" == "ru" ]]; then echo "Выберите Enter, 1, 2, 3 или q."; else echo "Choose Enter, 1, 2, 3 or q."; fi ;;
    esac
  done
}

# No non-language arguments + terminal => full visual wizard.
if [[ $# -eq 0 ]]; then
  if is_tty; then interactive=1; else usage; exit 2; fi
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interactive) interactive=1; shift ;;
    --detect-agents) detect_requested=1; agent_selection_mode="detected"; shift ;;
    --list-agents) list_requested=1; shift ;;
    --agents) agents_arg="${2:?missing value for --agents}"; agent_selection_mode="cli"; shift 2 ;;
    --agents=*) agents_arg="${1#*=}"; agent_selection_mode="cli"; shift ;;
    --scope) scope="${2:?missing value for --scope}"; scope_explicit=1; shift 2 ;;
    --scope=*) scope="${1#*=}"; scope_explicit=1; shift ;;
    --project) project="${2:?missing value for --project}"; shift 2 ;;
    --project=*) project="${1#*=}"; shift ;;
    --auto) auto_integration=1; integration_explicit=1; shift ;;
    --no-auto) auto_integration=0; integration_explicit=1; shift ;;
    --behavior) behavior="${2:?missing value for --behavior}"; settings_cli+=(--behavior "$behavior"); shift 2 ;;
    --behavior=*) behavior="${1#*=}"; settings_cli+=(--behavior "$behavior"); shift ;;
    --prompt-scope) prompt_scope="${2:?missing value for --prompt-scope}"; settings_cli+=(--prompt-scope "$prompt_scope"); shift 2 ;;
    --prompt-scope=*) prompt_scope="${1#*=}"; settings_cli+=(--prompt-scope "$prompt_scope"); shift ;;
    --quality-gate) quality_gate="${2:?missing value for --quality-gate}"; settings_cli+=(--quality-gate "$quality_gate"); shift 2 ;;
    --quality-gate=*) quality_gate="${1#*=}"; settings_cli+=(--quality-gate "$quality_gate"); shift ;;
    --unsupported-model) unsupported_model="${2:?missing value for --unsupported-model}"; settings_cli+=(--unsupported-model "$unsupported_model"); shift 2 ;;
    --unsupported-model=*) unsupported_model="${1#*=}"; settings_cli+=(--unsupported-model "$unsupported_model"); shift ;;
    --python-bin) PYTHON_BIN="${2:?missing value for --python-bin}"; shift 2 ;;
    --python-bin=*) PYTHON_BIN="${1#*=}"; shift ;;
    --backup) backup=on; shift ;;
    --no-backup) backup=off; shift ;;
    --dry-run) dry_run=1; shift ;;
    --doctor|--status) doctor_mode=1; shift ;;
    --uninstall) uninstall_mode=1; shift ;;
    -y|--yes) assume_yes=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) if [[ "$UI_LANG" == "ru" ]]; then echo "Неизвестный параметр: $1" >&2; else echo "Unknown option: $1" >&2; fi; usage >&2; exit 2 ;;
  esac
done

if [[ $interactive -eq 1 && $uninstall_mode -eq 0 && $doctor_mode -eq 0 ]]; then interactive_wizard; fi

case "$scope" in project|global) ;; *) if [[ "$UI_LANG" == ru ]]; then echo "Недопустимая область установки: $scope" >&2; else echo "Invalid scope: $scope" >&2; fi; exit 2;; esac
case "$behavior" in auto|preview|off) ;; *) if [[ "$UI_LANG" == ru ]]; then echo "Недопустимый режим: $behavior" >&2; else echo "Invalid behavior: $behavior" >&2; fi; exit 2;; esac
case "$prompt_scope" in all|first) ;; *) if [[ "$UI_LANG" == ru ]]; then echo "Недопустимый scope запросов: $prompt_scope" >&2; else echo "Invalid prompt scope: $prompt_scope" >&2; fi; exit 2;; esac
case "$quality_gate" in on|off|pass|light|full|adaptive) ;; *) if [[ "$UI_LANG" == ru ]]; then echo "Недопустимое значение Quality Gate: $quality_gate" >&2; else echo "Invalid quality gate: $quality_gate" >&2; fi; exit 2;; esac
case "$unsupported_model" in skip|generic) ;; *) if [[ "$UI_LANG" == ru ]]; then echo "Недопустимая политика неизвестной модели: $unsupported_model" >&2; else echo "Invalid unknown-model policy: $unsupported_model" >&2; fi; exit 2;; esac
if [[ $doctor_mode -eq 1 && $uninstall_mode -eq 1 ]]; then
  if [[ "$UI_LANG" == ru ]]; then echo "Выберите либо --doctor, либо --uninstall, но не оба параметра." >&2; else echo "Choose either --doctor or --uninstall, not both." >&2; fi
  exit 2
fi

if [[ $detect_requested -eq 1 ]]; then
  if [[ -n "$agents_arg" ]]; then
    if [[ "$UI_LANG" == ru ]]; then echo "Используйте либо --detect-agents, либо --agents, но не оба сразу." >&2; else echo "Use either --detect-agents or --agents, not both." >&2; fi
    exit 2
  fi
fi
[[ $detect_requested -eq 1 ]] && { agents_arg=auto; agent_selection_mode="detected"; }
if [[ $uninstall_mode -eq 1 && -n "$agents_arg" && "$agents_arg" != all ]]; then
  if [[ "$UI_LANG" == ru ]]; then echo "Uninstall удаляет всю установку; не указывайте --agents или используйте --agents all." >&2; else echo "Uninstall removes the complete installation; omit --agents or use --agents all." >&2; fi
  exit 2
fi

if ! resolve_python; then
  if [[ "$UI_LANG" == ru ]]; then echo "Требуется Python 3. Если он установлен под другим именем, задайте PYTHON_BIN." >&2; else echo "Python 3 is required. Set PYTHON_BIN if it is installed under another name." >&2; fi
  exit 1
fi

if [[ $list_requested -eq 1 ]]; then
  exec "$PYTHON_BIN" -B "$SCRIPT_DIR/install.py" --lang "$UI_LANG" --scope "$scope" --project "$project" --list-agents
fi

if [[ $doctor_mode -eq 1 ]]; then
  exec "$PYTHON_BIN" -B "$SCRIPT_DIR/install.py" --lang "$UI_LANG" --scope "$scope" --project "$project" --doctor
fi

if [[ $assume_yes -eq 0 && $scope_explicit -eq 0 && ( $interactive -eq 0 || $uninstall_mode -eq 1 ) ]] && is_tty; then
  configure_scope_interactive
fi

if [[ -z "$agents_arg" && "$agent_selection_mode" != detected ]]; then
  if [[ "$scope" == global && $uninstall_mode -eq 0 ]]; then
    agents_arg=auto; agent_selection_mode="auto"
  else
    agents_arg=all; agent_selection_mode="all"
  fi
fi

if [[ $uninstall_mode -eq 1 && $assume_yes -eq 0 ]] && is_tty; then
  header
  if [[ "$UI_LANG" == ru ]]; then
    echo "Будет полностью удалена выбранная установка Prompt Optimizer, включая изменённые файлы пакета. Пользовательские файлы и настройки будут сохранены."
    echo "Область: $scope"
    [[ "$scope" == project ]] && echo "Путь: $project"
    read -r -p "Введите uninstall для продолжения: " answer || true
  else
    echo "The selected Prompt Optimizer installation will be completely removed, including modified package files. User-owned files and settings will be preserved."
    echo "Scope: $scope"
    [[ "$scope" == project ]] && echo "Path: $project"
    read -r -p "Type uninstall to continue: " answer || true
  fi
  [[ "$(lower "$answer")" == uninstall ]] || { echo "$(tr_ui cancelled)"; exit 0; }
elif [[ $interactive -eq 0 && $assume_yes -eq 0 ]] && is_tty; then
  header; show_summary
  if [[ "$UI_LANG" == ru ]]; then read -r -p "Нажмите Enter для продолжения или q для отмены: " answer || true; else read -r -p "Press Enter to continue, or q to cancel: " answer || true; fi
  if [[ "$(lower "$answer")" == q ]]; then echo "$(tr_ui cancelled)"; exit 0; fi
fi

cmd=("$PYTHON_BIN" -B "$SCRIPT_DIR/install.py" --lang "$UI_LANG" --scope "$scope" --project "$project" --python-bin "$PYTHON_BIN" --yes)
if [[ "$agent_selection_mode" == detected ]]; then
  cmd+=(--detect-agents)
elif [[ "$agent_selection_mode" != auto && ( "$agent_selection_mode" != all || $interactive -eq 1 ) ]]; then
  cmd+=(--agents "$agents_arg")
fi
# Defaults do not overwrite settings on a repeat installation. Wizard choices
# and explicit flags are intentional overrides; Python resolves saved values.
if [[ $interactive -eq 1 && $uninstall_mode -eq 0 ]]; then
  cmd+=(--behavior "$behavior" --prompt-scope "$prompt_scope" --quality-gate "$quality_gate" --unsupported-model "$unsupported_model")
  [[ $auto_integration -eq 1 ]] && cmd+=(--auto) || cmd+=(--no-auto)
else
  cmd+=("${settings_cli[@]}")
  if [[ $integration_explicit -eq 1 ]]; then
    [[ $auto_integration -eq 1 ]] && cmd+=(--auto) || cmd+=(--no-auto)
  else
    # The shell launcher retains its native-integration default for first installs.
    cmd+=(--default-auto)
  fi
fi
[[ "$backup" == off ]] && cmd+=(--no-backup)
[[ $dry_run -eq 1 ]] && cmd+=(--dry-run)
[[ $uninstall_mode -eq 1 ]] && cmd+=(--uninstall)

exec "${cmd[@]}"
