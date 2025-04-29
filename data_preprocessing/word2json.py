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
    role: str  # 'client' or 'psychologist'
    content: str


@dataclass
class Dialogue:
    dialogue_id: int
    topic: Optional[str]
    messages: List[Message] = field(default_factory=list)


HEADER_PATTERN = re.compile(
    r'^Диалог\s+(\d+)'                       # номер диалога
    r'(?:\s*[«"]([^»"]+)[»"]|\s+(.+))?'      # опциональная тема в «» или без кавычек
    r'$'
)


def parse_docx(path: Path) -> List[Dialogue]:
    """
    Прочитать .docx и спарсить диалоги по структуре:
      Диалог N [«Тема»]
      Клиент:
        текст...
      Психолог:
        текст...
    Берёт в расчёт случаи, когда внутри одной строки может идти сразу
    и клиентская фраза, и маркер "Психолог: ...".
    """
    doc = docx.Document(path)
    dialogues: List[Dialogue] = []
    current: Optional[Dialogue] = None
    current_role: Optional[str] = None
    buffer: List[str] = []

    def flush_message():
        nonlocal buffer, current_role, current
        if current and current_role and buffer:
            text = "\n".join(line.strip() for line in buffer).strip()
            if text:
                current.messages.append(Message(role=current_role, content=text))
            buffer = []

    for para in doc.paragraphs:
        raw = para.text.strip()
        if not raw:
            continue

        # разбиваем по вкраплениям "Клиент:" или "Психолог:" внутри строки
        segments = re.split(r'(?=(?:Клиент:|Психолог:))', raw)
        for line in segments:
            line = line.strip()
            if not line:
                continue

            # проверяем начало нового диалога
            m = HEADER_PATTERN.match(line)
            if m:
                # завершаем предыдущий
                if current:
                    flush_message()
                    dialogues.append(current)

                dlg_id = int(m.group(1))
                topic = (m.group(2) or m.group(3) or "").strip() or None
                current = Dialogue(dialogue_id=dlg_id, topic=topic)
                logger.info(f"Found dialogue {dlg_id}" + (f" with topic '{topic}'" if topic else ""))
                current_role = None
                buffer = []
                continue

            # проверяем новую реплику клиента
            if line.startswith("Клиент:"):
                flush_message()
                current_role = "client"
                buffer = [line[len("Клиент:"):].strip()]
            # проверяем новую реплику психолога
            elif line.startswith("Психолог:"):
                flush_message()
                current_role = "psychologist"
                buffer = [line[len("Психолог:"):].strip()]
            else:
                # продолжение текущей реплики
                if current_role:
                    buffer.append(line)
                else:
                    logger.warning(f"Ignoring line outside of any speaker: {line}")

    # не забываем последний диалог
    if current:
        flush_message()
        dialogues.append(current)

    return dialogues



def export_to_json(dialogues: List[Dialogue], out_path: Path):
    """
    Сохраняет список Dialogue в JSON-файл:
    [
      {
        "dialogue_id": 1,
        "topic": "...",
        "messages": [
          {"role": "client", "content": "..."},
          {"role": "psychologist", "content": "..."},
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
        description="Convert psychological dialogues from .docx to JSON for ChatGPT fine-tuning."
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
        default=Path("dataset_2.json"),
        help="Path for the output .json file (default: %(default)s)"
    )
    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return

    dialogues = parse_docx(args.input)
    if not dialogues:
        logger.error("No dialogues found in the document.")
        return

    export_to_json(dialogues, args.output)
    logger.info("Conversion completed successfully.")


if __name__ == "__main__":
    main()

