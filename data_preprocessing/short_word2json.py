#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

import docx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str       # 'client' or 'psychologist'
    content: str


@dataclass
class Dialogue:
    dialogue_id: int
    topic: Optional[str]
    messages: List[Message] = field(default_factory=list)


# Заголовок: (🔹)Диалог N [тема]
HEADER_PATTERN = re.compile(
    r'^\s*(?:🔹\s*)?Диалог\s+(\d+)(?:\s+(.+?))?\s*$'
)

# Удаляем эмоджи/пиктограммы
EMOJI_PATTERN = re.compile(
    "["                            
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols, etc.
    "]+",
    flags=re.UNICODE
)


def strip_emoji(text: str) -> str:
    """Удалить эмоджи и ненужные маркеры."""
    return EMOJI_PATTERN.sub("", text).strip()


def parse_docx(path: Path) -> List[Dialogue]:
    """
    Прочитать .docx и спарсить диалоги:
      - Заголовок "Диалог N [тема]"
      - Реплики "Клиент:" и "Психолог:"
      - Вложенные внутри строки speaker-теги корректно разделяются
    """
    doc = docx.Document(path)
    dialogues: List[Dialogue] = []
    current: Optional[Dialogue] = None
    current_role: Optional[str] = None
    buffer: List[str] = []

    def flush_message():
        """Добавить накопленный буфер в текущий диалог как одно сообщение."""
        nonlocal buffer, current_role, current
        if current and current_role and buffer:
            content = " ".join(line.strip() for line in buffer).strip()
            if content:
                current.messages.append(Message(role=current_role, content=content))
        buffer = []

    for para in doc.paragraphs:
        raw = para.text.strip()
        if not raw:
            continue

        # Убираем эмоджи/маркеры
        line = strip_emoji(raw)

        # Проверяем, начало ли это нового диалога
        m = HEADER_PATTERN.match(line)
        if m:
            # Завершаем предыдущий диалог
            if current:
                flush_message()
                dialogues.append(current)

            dlg_id = int(m.group(1))
            topic_raw = m.group(2).strip() if m.group(2) else None
            topic = re.sub(r'[^0-9A-Za-zА-Яа-яЁё\s]+', '', topic_raw).strip() if topic_raw else None
            current = Dialogue(dialogue_id=dlg_id, topic=topic)
            logger.info(f"Found dialogue {dlg_id}" + (f" with topic '{topic}'" if topic else ""))
            current_role = None
            buffer = []
            continue

        # Если ещё нет текущего диалога, пропускаем
        if current is None:
            logger.warning(f"Ignoring line before any dialogue header: {line}")
            continue

        # Разбиваем по вкраплениям "Клиент:" и "Психолог:"
        segments = re.split(r'(?=(?:Клиент:|Психолог:))', line)
        for seg in segments:
            text = seg.strip()
            if not text:
                continue

            if text.startswith("Клиент:"):
                flush_message()
                current_role = "client"
                buffer = [text[len("Клиент:"):].strip()]

            elif text.startswith("Психолог:"):
                flush_message()
                current_role = "psychologist"
                buffer = [text[len("Психолог:"):].strip()]

            else:
                # Продолжение последнего спикера
                if current_role:
                    buffer.append(text)
                else:
                    logger.warning(f"Ignoring orphan text: {text}")

    # Завершаем последний диалог
    if current:
        flush_message()
        dialogues.append(current)

    return dialogues


def export_to_json(dialogues: List[Dialogue], out_path: Path):
    """
    Сохранить список диалогов в JSON:
    [
      {
        "dialogue_id": ...,
        "topic": "...",
        "messages": [
          {"role": "client", "content": "..."},
          ...
        ]
      },
      ...
    ]
    """
    data = []
    for dlg in dialogues:
        data.append({
            "dialogue_id": dlg.dialogue_id,
            "topic": dlg.topic,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in dlg.messages
            ]
        })

    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info(f"Exported {len(dialogues)} dialogues to {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert short psychological dialogues from .docx to JSON."
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=Path("../data_preprocessing/dataset_2.docx"),
        help="Path to the input .docx file (default: %(default)s)"
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path("short_dataset_2.json"),
        help="Path for the output .json file (default: %(default)s)"
    )
    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return

    dialogues = parse_docx(args.input)
    if not dialogues:
        logger.error("No dialogues found.")
        return

    export_to_json(dialogues, args.output)


if __name__ == "__main__":
    main()
