<div align="center">

<img src="new_logo2.png" alt="GreyClaw" width="600">

<br/>

# Просто разговаривайте с вашим агентом, и он будет учиться и *ЭВОЛЮЦИОНИРОВАТЬ*.

<p>Вдохновлено тем, как учится мозг. Мета-обучение и эволюция вашего 🦞 в каждом реальном диалоге. GPU не требуется. Поддерживает Kimi, Qwen, Claude, MiniMax и другие.</p>

<img src="greyclaw_mainfig_v2.png" alt="GreyClaw Architecture" width="800">

<p>
  <a href="https://github.com/aiming-lab/GreyClaw"><img src="https://img.shields.io/badge/github-GreyClaw-181717?style=flat&labelColor=555&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat&labelColor=555" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/⚡_Полностью_асинхронно-yellow?style=flat&labelColor=555" alt="Fully Async" />
  <img src="https://img.shields.io/badge/☁️_Без_GPU_кластера-blue?style=flat&labelColor=555" alt="No GPU Cluster" />
  <img src="https://img.shields.io/badge/🛠️_Эволюция_навыков-orange?style=flat&labelColor=555" alt="Skill Evolution" />
  <img src="https://img.shields.io/badge/🚀_Развертывание_в_один_клик-green?style=flat&labelColor=555" alt="One-Click Deploy" />
</p>

<br/>

[🇺🇸 English](../README.md) • [🇨🇳 中文](./README_ZH.md) • [🇯🇵 日本語](./README_JA.md) • [🇰🇷 한국어](./README_KO.md) • [🇫🇷 Français](./README_FR.md) • [🇩🇪 Deutsch](./README_DE.md) • [🇪🇸 Español](./README_ES.md) • [🇧🇷 Português](./README_PT.md) • [🇮🇹 Italiano](./README_IT.md) • [🇻🇳 Tiếng Việt](./README_VI.md) • [🇸🇦 العربية](./README_AR.md) • [🇮🇳 हिन्दी](./README_HI.md)

<br/>

[Обзор](#-обзор) • [Быстрый старт](#-быстрый-старт) • [Конфигурация](#️-конфигурация) • [Режим навыков](#-режим-навыков) • [Режим RL](#-режим-rl) • [Режим MadMax](#-режим-madmax-по-умолчанию) • [Цитирование](#-цитирование)

</div>

---

<div align="center">

### Две команды. Это все.
</div>

```bash
greyclaw setup              # одноразовый мастер настройки
greyclaw start              # по умолчанию: режим madmax, навыки + плановое RL-обучение
greyclaw start --daemon     # запуск в фоновом режиме, логи -> ~/.greyclaw/greyclaw.log
greyclaw start --daemon --log-file /tmp/greyclaw.log  # пользовательский путь к логу
greyclaw start --mode rl    # RL без планировщика (обучение сразу по заполнении batch)
greyclaw start --mode skills_only  # только навыки, без RL (Tinker не нужен)
```

<div align="center">
<img src="greyclaw.gif" alt="GreyClaw demo" width="700">
</div>

---

## 🔥 Новости

- **[16.03.2026]** **v0.3.2** Поддержка нескольких Claw: IronClaw, PicoClaw, ZeroClaw, CoPaw, NanoClaw и NemoClaw теперь поддерживаются наряду с OpenClaw. NanoClaw через новый эндпоинт `/v1/messages`, совместимый с Anthropic; NemoClaw через маршрутизацию инференса OpenShell. Добавлен OpenRouter как поддерживаемая платформа LLM.
- **[13.03.2026]** **v0.3.1** Поддержка бэкенда MinT: RL-обучение теперь работает как с Tinker, так и с MinT. Настраивается через `rl.backend` (auto/tinker/mint).
- **[13.03.2026]** **v0.3** Поддержка непрерывного мета-обучения: медленные RL-обновления запускаются только во время сна, простоя или встреч в Google Calendar. Добавлено разделение на support/query множества для предотвращения загрязнения обновлений модели устаревшими сигналами вознаграждения.
- **[11.03.2026]** **v0.2** Развертывание в один клик через CLI `greyclaw`. Навыки включены по умолчанию, RL теперь опционален.
- **[09.03.2026]** Выпущен **GreyClaw**. Просто общайтесь с агентом, и он будет эволюционировать автоматически. GPU-развертывание **не требуется**, достаточно подключить **API**.

---

## 🎥 Демонстрация

https://github.com/user-attachments/assets/d86a41a8-4181-4e3a-af0e-dc453a6b8594

---

## 📖 Обзор

**GreyClaw это агент, который мета-обучается и эволюционирует в реальных условиях.**
Просто общайтесь с агентом, как обычно. GreyClaw превращает каждый живой диалог в обучающий сигнал, позволяя агенту непрерывно совершенствоваться через реальное развертывание, а не только через офлайн-обучение.

Под капотом GreyClaw размещает вашу модель за OpenAI-совместимым прокси (для Anthropic-нативных агентов вроде NanoClaw дополнительно предоставляется `/v1/messages`-совместимый эндпоинт), который перехватывает взаимодействия через OpenClaw, NanoClaw, NemoClaw и другие поддерживаемые агенты, внедряет релевантные навыки на каждом шаге и мета-обучается на накопленном опыте. После каждой сессии навыки автоматически суммируются; при включенном RL планировщик мета-обучения откладывает обновление весов до окон простоя, чтобы агент не прерывался во время активного использования.

GPU-кластер не требуется. GreyClaw работает с любым OpenAI-совместимым LLM API «из коробки» и использует Tinker-совместимый бэкенд для облачного LoRA-дообучения. [Tinker](https://www.thinkingmachines.ai/tinker/) является путем по умолчанию, а MinT можно подключить через отдельный пакет совместимости при необходимости.

## 🤖 Ключевые возможности

### **Развертывание в один клик**
Настройте один раз с помощью `greyclaw setup`, затем `greyclaw start` запускает прокси, внедряет навыки и автоматически подключает OpenClaw. Ручные shell-скрипты не нужны.

### **Три режима работы**

| Режим | По умолчанию | Описание |
|-------|-------------|----------|
| `skills_only` | | Прокси для вашего LLM API. Навыки внедряются, после каждой сессии автоматически суммируются. GPU/Tinker не требуются. |
| `rl` | | Навыки + RL-обучение (GRPO). Обучение запускается сразу при заполнении batch. Опциональный OPD для дистилляции учителя. |
| `madmax` | ✅ | Навыки + RL + интеллектуальный планировщик. Обновление весов RL происходит только во время сна/простоя/встреч. |

### **Полностью асинхронная архитектура**
Обслуживание, моделирование вознаграждений и обучение полностью разделены. Агент продолжает отвечать, пока оценка и оптимизация выполняются параллельно.

---

## 🚀 Быстрый старт

### 1. Установка

```bash
pip install -e .                        # режим skills_only (легковесный)
pip install -e ".[rl]"                  # + поддержка RL-обучения (torch, transformers, tinker)
pip install -e ".[evolve]"              # + эволюция навыков через OpenAI-совместимый LLM
pip install -e ".[scheduler]"           # + интеграция с Google Calendar для планировщика
pip install -e ".[rl,evolve,scheduler]" # рекомендуется для полной конфигурации RL + планировщик
```

Если вы хотите использовать `rl.backend=mint`, установите пакет совместимости MinT отдельно в том же окружении, например [`mindlab-toolkit`](https://github.com/MindLab-Research/mindlab-toolkit). GreyClaw не включает эту зависимость в пакет по умолчанию, чтобы пользователи RL могли явно выбирать между Tinker и MinT.

### 2. Настройка

```bash
greyclaw setup
```

Интерактивный мастер предложит выбрать LLM-провайдера (Kimi, Qwen, MiniMax или пользовательский), ввести API-ключ и опционально включить RL-обучение.

RL-путь GreyClaw позволяет явно переключаться между `tinker` и `mint`. Рекомендуемое значение по умолчанию: `auto`. При установленном пакете MinT он по-прежнему способен распознать MinT по учетным данным или base URL в стиле Mint.

**Tinker** (по умолчанию):

```bash
greyclaw config rl.backend tinker
greyclaw config rl.api_key sk-...
greyclaw config rl.model moonshotai/Kimi-K2.5
```

**MinT**:

```bash
greyclaw config rl.backend mint
greyclaw config rl.api_key sk-mint-...
greyclaw config rl.base_url https://mint.macaron.xin/
greyclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
```

Устаревшие псевдонимы `rl.tinker_api_key` и `rl.tinker_base_url` по-прежнему поддерживаются для обратной совместимости.

### 3. Запуск

```bash
greyclaw start
```

Это все. GreyClaw запускает прокси, автоматически настраивает OpenClaw и перезапускает шлюз. Откройте OpenClaw и начните диалог: навыки внедряются на каждом шаге, а по завершении сессии автоматически суммируются в новые навыки.

---

## ⚙️ Конфигурация

Файл конфигурации находится в `~/.greyclaw/config.yaml` и создается командой `greyclaw setup`.

**Команды CLI:**

```
greyclaw setup                  # Интерактивный мастер первоначальной настройки
greyclaw start                  # Запуск GreyClaw (по умолчанию: режим madmax)
greyclaw start --daemon         # Запуск GreyClaw в фоновом режиме
greyclaw start --daemon --log-file /tmp/greyclaw.log  # Пользовательский путь к логу
greyclaw start --mode rl        # Принудительно включить режим RL (без планировщика) для этой сессии
greyclaw start --mode skills_only  # Принудительно включить режим только навыков для этой сессии
greyclaw stop                   # Остановить работающий экземпляр GreyClaw
greyclaw status                 # Проверить состояние прокси, режим работы и статус планировщика
greyclaw config show            # Просмотр текущей конфигурации
greyclaw config KEY VALUE       # Установить значение конфигурации
```

При запуске GreyClaw с `--daemon` команда ожидает, пока локальный прокси станет доступен, прежде чем вернуть управление. Используйте `greyclaw status` для проверки состояния и `greyclaw stop` для остановки фонового процесса.

<details>
<summary><b>Полная справка по конфигурации (нажмите, чтобы развернуть)</b></summary>

```yaml
mode: madmax               # "madmax" | "rl" | "skills_only"

llm:
  provider: kimi            # kimi | qwen | openai | minimax | custom
  model_id: moonshotai/Kimi-K2.5
  api_base: https://api.moonshot.cn/v1
  api_key: sk-...

proxy:
  port: 30000
  api_key: ""              # необязательный bearer-токен для локального прокси GreyClaw

skills:
  enabled: true
  dir: ~/.greyclaw/skills   # каталог вашей библиотеки навыков
  retrieval_mode: template  # template | embedding
  top_k: 6
  task_specific_top_k: 10   # лимит навыков для конкретных задач (по умолчанию 10)
  auto_evolve: true         # автоматическое суммирование навыков после каждой сессии

rl:
  enabled: false            # установите true для включения RL-обучения
  backend: auto             # "auto" | "tinker" | "mint"
  model: moonshotai/Kimi-K2.5
  api_key: ""
  base_url: ""              # необязательная точка доступа бэкенда, например https://mint.macaron.xin/ для MinT
  tinker_api_key: ""        # устаревший псевдоним для api_key
  tinker_base_url: ""       # устаревший псевдоним для base_url
  prm_url: https://api.openai.com/v1
  prm_model: gpt-5.2
  prm_api_key: ""
  lora_rank: 32
  batch_size: 4
  resume_from_ckpt: ""      # необязательный путь к контрольной точке для возобновления обучения
  evolver_api_base: ""      # оставьте пустым для использования llm.api_base
  evolver_api_key: ""
  evolver_model: gpt-5.2

opd:
  enabled: false            # установите true для включения OPD (дистилляция учителя)
  teacher_url: ""           # base URL модели-учителя (OpenAI-совместимый /v1/completions)
  teacher_model: ""         # имя модели-учителя (например, Qwen/Qwen3-32B)
  teacher_api_key: ""       # API-ключ модели-учителя
  kl_penalty_coef: 1.0      # коэффициент KL-штрафа для OPD

max_context_tokens: 20000   # лимит токенов промпта перед усечением

scheduler:                  # v0.3: планировщик мета-обучения (автоматически включается в режиме madmax)
  enabled: false            # в режиме madmax включается автоматически; для режима rl установите вручную
  sleep_start: "23:00"
  sleep_end: "07:00"
  idle_threshold_minutes: 30
  min_window_minutes: 15
  calendar:
    enabled: false
    credentials_path: ""
    token_path: ""
```

</details>

---

## 💪 Режим навыков

**`greyclaw start --mode skills_only`**

Самый легкий режим. Не требуется ни GPU, ни RL-бэкенд. GreyClaw размещает ваш LLM за прокси, который внедряет релевантные навыки на каждом шаге, а затем автоматически суммирует новые навыки после каждого диалога.

Навыки представляют собой короткие Markdown-инструкции, хранящиеся в `~/.greyclaw/skills/` в виде отдельных файлов `SKILL.md`. Библиотека навыков растет автоматически вместе с использованием.

Для предварительной загрузки встроенного банка навыков (более 40 навыков по программированию, безопасности, агентным задачам и др.):

```bash
cp -r memory_data/skills/* ~/.greyclaw/skills/
```

---

## 🔬 Режим RL

**`greyclaw start --mode rl`**

Все возможности режима навыков плюс непрерывное RL-дообучение на основе живых диалогов. Каждый шаг диалога токенизируется и отправляется как обучающий пример. Модель-судья (PRM) асинхронно оценивает ответы, а Tinker-совместимый бэкенд (Tinker cloud или MinT) выполняет LoRA-дообучение с горячей заменой весов.

**Tinker** (по умолчанию):

```bash
greyclaw config rl.backend tinker
greyclaw config rl.api_key sk-...
greyclaw config rl.model moonshotai/Kimi-K2.5
greyclaw config rl.prm_url https://api.openai.com/v1
greyclaw config rl.prm_api_key sk-...
greyclaw start --mode rl
```

**MinT**:

```bash
greyclaw config rl.backend mint
greyclaw config rl.api_key sk-mint-...
greyclaw config rl.base_url https://mint.macaron.xin/
greyclaw config rl.model Qwen/Qwen3-4B-Instruct-2507
greyclaw config rl.prm_url https://api.openai.com/v1
greyclaw config rl.prm_api_key sk-...
greyclaw start --mode rl
```

Специализированная модель-эволюционер также извлекает новые навыки из неудачных эпизодов и возвращает их в библиотеку навыков.

**Программный rollout** (без TUI OpenClaw): установите `openclaw_env_data_dir` на каталог с JSONL-файлами задач:

```json
{"task_id": "task_1", "instruction": "Register the webhook at https://example.com/hook"}
```

### Дистилляция с политикой на лету (OPD)

OPD является опциональным дополнением к режиму RL. Он дистиллирует большую модель-учителя в модель-ученика на его собственной политике: ученик генерирует ответы как обычно, а учитель предоставляет потокенные логарифмические вероятности для тех же ответов. KL-штраф направляет ученика к распределению учителя.

```bash
greyclaw config opd.enabled true
greyclaw config opd.teacher_url http://localhost:8082/v1
greyclaw config opd.teacher_model Qwen/Qwen3-32B
greyclaw config opd.kl_penalty_coef 1.0
```

Учитель должен быть развернут за OpenAI-совместимой точкой доступа `/v1/completions` (например, vLLM, SGLang). OPD можно комбинировать с оценкой PRM, оба процесса выполняются асинхронно. См. `examples/run_conversation_opd.py` и `scripts/run_openclaw_tinker_opd.sh`.

---

## 🧠 Режим MadMax (По умолчанию)

**`greyclaw start`**

Все возможности режима RL плюс планировщик мета-обучения, который откладывает обновление весов до окон неактивности пользователя, чтобы агент не прерывался во время активного использования. Это режим по умолчанию.

Шаг горячей замены весов RL приостанавливает агента на несколько минут. Вместо того чтобы обучаться сразу при заполнении batch (как в режиме RL), MadMax ожидает подходящего окна.

Три условия запускают окно обновления (достаточно любого одного):

- **Часы сна**: настраиваемое время начала/окончания (например, 23:00 до 07:00)
- **Неактивность клавиатуры**: срабатывает после N минут простоя
- **События Google Calendar**: обнаруживает встречи, чтобы обновления выполнялись, пока вы отсутствуете

```bash
greyclaw config scheduler.sleep_start "23:00"
greyclaw config scheduler.sleep_end   "07:00"
greyclaw config scheduler.idle_threshold_minutes 30

# Необязательно: интеграция с Google Calendar
pip install -e ".[scheduler]"
greyclaw config scheduler.calendar.enabled true
greyclaw config scheduler.calendar.credentials_path ~/.greyclaw/client_secrets.json
```

Если пользователь возвращается во время обновления, частичный batch сохраняется и возобновляется в следующем окне.

Каждый `ConversationSample` помечается версией `skill_generation`. Когда эволюция навыков увеличивает поколение, RL-буфер очищается, и для градиентных обновлений используются только пост-эволюционные примеры (разделение MAML support/query множеств).

---

## 📚 Цитирование

```bibtex
@misc{xia2026greyclaw,
  author       = {Xia, Peng and Chen, Jianwen and Yang, Xinyu and Tu, Haoqin and Han, Siwei and Qiu, Shi and Zheng, Zeyu and Xie, Cihang and Yao, Huaxiu},
  title        = {GreyClaw: Just Talk --- An Agent That Meta-Learns and Evolves in the Wild},
  year         = {2026},
  organization = {GitHub},
  url          = {https://github.com/aiming-lab/GreyClaw},
}
```

---

## 🙏 Благодарности

GreyClaw построен на основе следующих проектов с открытым исходным кодом:

- [OpenClaw](https://openclaw.ai), основной фреймворк агента.
- [SkillRL](https://github.com/aiming-lab/SkillRL), наш фреймворк RL с расширением навыков.
- [Tinker](https://www.thinkingmachines.ai/tinker/), используется для онлайн RL-обучения.
- [MinT](https://github.com/MindLab-Research/mindlab-toolkit), альтернативный бэкенд для онлайн RL-обучения.
- [OpenClaw-RL](https://github.com/Gen-Verse/OpenClaw-RL), вдохновение для нашего дизайна RL.
- [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills), основа для нашего банка навыков.
- [NanoClaw](https://github.com/qwibitai/nanoclaw), персональный Claude-агент от qwibitai, подключается через `/v1/messages`-совместимый эндпоинт Anthropic.
- [NemoClaw](https://github.com/NVIDIA/NemoClaw), плагин агента OpenShell от NVIDIA для инференса.

---

## 📄 Лицензия

Этот проект распространяется под лицензией [MIT](LICENSE).
