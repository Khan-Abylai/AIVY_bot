#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import argparse
from pathlib import Path

import docx

# Убираем эмодзи
EMOJI_PATTERN = re.compile(
    "["                            
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "]+",
    flags=re.UNICODE
)

# Заголовок: "Диалог N [тема]"
HEADER_PATTERN = re.compile(r'^\s*Диалог\s+(\d+)\s*(.*)$', re.IGNORECASE)
# Маркер конца диалога
MODULE_PATTERN = re.compile(r'Переход на модуль\s*(\d+)', re.IGNORECASE)

def strip_emoji(text: str) -> str:
    return EMOJI_PATTERN.sub("", text).strip()

def clean_topic(raw: str) -> str:
    no_emoji = strip_emoji(raw)
    # оставляем только буквы и пробелы
    return re.sub(r'[^А-Яа-яЁёA-Za-z\s]', '', no_emoji).strip()

def parse_docx(path: Path):
    doc = docx.Document(path)
    dialogues = []
    current = None
    current_role = None
    buffer: list[str] = []

    def flush_message():
        nonlocal buffer, current_role, current
        if current and current_role and buffer:
            content = " ".join(buffer).strip()
            if content:
                current["messages"].append({
                    "role": current_role,
                    "content": content
                })
        buffer.clear()

    for para in doc.paragraphs:
        raw = para.text.strip()
        if not raw:
            continue

        line = strip_emoji(raw)

        # Если увидели "Переход на модуль N" — закрываем текущий диалог
        if MODULE_PATTERN.search(line):
            flush_message()
            # добавляем это сообщение как последнее от психолога
            if current:
                current["messages"].append({
                    "role": "psychologist",
                    "content": MODULE_PATTERN.search(line).group(0)
                })
                dialogues.append(current)
            # больше не держим active current
            current = None
            current_role = None
            buffer.clear()
            continue

        # Если заголовок "Диалог N [тема]" — начинаем новый
        m_hdr = HEADER_PATTERN.match(line)
        if m_hdr:
            if current:
                flush_message()
                dialogues.append(current)
            dlg_id = int(m_hdr.group(1))
            topic = clean_topic(m_hdr.group(2))
            current = {
                "dialogue_id": dlg_id,
                "topic": topic or None,
                "messages": []
            }
            current_role = None
            buffer.clear()
            continue

        # Если диалог не открыт — пропускаем
        if not current:
            continue

        # Иначе парсим реплики
        parts = re.split(r'(?=(?:Клиент:|Психолог:))', line)
        for part in parts:
            text = part.strip()
            if not text:
                continue
            if text.startswith("Клиент:"):
                flush_message()
                current_role = "client"
                buffer.clear()
                buffer.append(text[len("Клиент:"):].strip())
            elif text.startswith("Психолог:"):
                flush_message()
                current_role = "psychologist"
                buffer.clear()
                buffer.append(text[len("Психолог:"):].strip())
            else:
                if current_role:
                    buffer.append(text)

    # Завершаем последний диалог, если остался
    if current:
        flush_message()
        dialogues.append(current)

    return dialogues

def export_to_json(dialogues, out_path: Path):
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(dialogues, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(dialogues)} dialogues to {out_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Парсинг .docx с психологическими диалогами в JSON"
    )
    parser.add_argument(
        'input', type=Path, nargs='?',
        default=Path("dataset_2.docx"),
        help="Путь к .docx файлу"
    )
    parser.add_argument(
        'output', type=Path, nargs='?',
        default=Path("dataset_2.json"),
        help="Путь для сохранения JSON"
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: file not found: {args.input}")
        return

    dialogues = parse_docx(args.input)
    export_to_json(dialogues, args.output)

if __name__ == "__main__":
    main()
