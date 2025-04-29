#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

# Путь к исходному JSON с полными диалогами
INPUT_JSON = Path("/Users/aazamatov/Documents/AIVY/AIVY_bot/data_preprocessing/aivi_dialogues_dataset_2.json")
# Путь к выходному файлу JSONL для fine‑tuning
OUTPUT_JSONL = Path("/Users/aazamatov/Documents/AIVY/AIVY_bot/data_preprocessing/train_data_2.jsonl")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Converter
# ------------------------------------------------------------------------------

def convert_to_jsonl(input_path: Path, output_path: Path) -> None:

    # 1) Проверим входной файл
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return

    # 2) Загрузим список диалогов
    try:
        raw_data: List[Dict[str, Any]] = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return

    out_lines: List[str] = []

    # 3) Преобразуем каждый диалог
    for dlg in raw_data:
        topic = dlg.get("topic")
        history: List[Dict[str, str]] = []

        # Добавляем тему как system-сообщение, если она не пустая
        if topic:
            history.append({
                "role": "system",
                "content": f"Тема разговора: {topic}"
            })

        # Пройдемся по репликам
        for msg in dlg.get("messages", []):
            # Переводим роли
            if msg.get("role") == "client":
                role = "user"
            else:
                role = "assistant"

            # Текст без префиксов, без переносов строк
            content = msg.get("content", "").replace("\n", " ").strip()
            if not content:
                continue  # пропустим пустые реплики

            history.append({
                "role": role,
                "content": content
            })

            # Когда встретили ответ assistant — сохраняем пример
            if role == "assistant":
                example = {"messages": history.copy()}
                out_lines.append(json.dumps(example, ensure_ascii=False))

    # 4) Сохраняем в JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(out_lines), encoding="utf-8")
    logger.info(f"✅ Prepared {len(out_lines)} examples into {output_path.resolve()}")


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    convert_to_jsonl(INPUT_JSON, OUTPUT_JSONL)
