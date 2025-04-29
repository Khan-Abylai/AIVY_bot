import docx
import json
import re

def process_dialogue(dialogue_text):
    """
    Обрабатывает один диалог:
    - Извлекает номер диалога и тему из заголовка.
      Заголовок может иметь произвольные эмоджи перед словом "Диалог", например:
      "🔹Диалог 1 — Усталость и раздражение (будни)"
    - Парсит каждую строку диалога, определяя спикера и текст.
    - Приводит имена "Ivy" и "психолог" к единому виду "Психолог".
    - При обнаружении строки, начинающейся с "→", динамически формирует сообщение перехода,
      например, "→ Модуль 1" превращается в "Переход на Модуль 1".
    """
    lines = dialogue_text.strip().split('\n')
    if not lines:
        return None

    # Заголовок может содержать эмоджи, поэтому допускаем наличие несловесных символов перед "Диалог"
    # Используем шаблон: необязательные неалфавитные символы, затем "Диалог", число, разделитель (—) и тему.
    header = lines[0].strip()
    header_match = re.match(r"^(?:\W+)?Диалог\s*(\d+)\s*[—-]\s*(.+)", header)
    if not header_match:
        return None

    dialogue_id = header_match.group(1).strip()
    topic = header_match.group(2).strip()
    utterances = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        # Если строка начинается с "→", формируем динамический переход (любого модуля)
        if line.startswith("→"):
            module_info = line.lstrip("→").strip()  # удаляем стрелку и пробелы
            transition_text = f"Переход на {module_info}"
            utterances.append({
                "speaker": "Система",
                "text": transition_text
            })
            continue

        # Парсим строки по шаблону "Спикер: Текст"
        speaker_match = re.match(r"([^:]+):\s*(.+)", line)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            text = speaker_match.group(2).strip()
            # Приводим имена к единому виду: "Ivy" и "психолог" → "Психолог"
            if speaker.lower() in ["ivy", "психолог"]:
                speaker = "Психолог"
            utterances.append({"speaker": speaker, "text": text})
        else:
            # Если строка не соответствует шаблону, добавляем её к предыдущему высказыванию
            if utterances:
                utterances[-1]["text"] += " " + line
            else:
                utterances.append({"speaker": "Неопределено", "text": line})

    return {
        "dialogue_id": dialogue_id,
        "topic": topic,
        "utterances": utterances
    }

def process_docx(file_path):
    """
    Читает Word‑файл, объединяет все параграфы и динамически разбивает текст на диалоги.
    Разбиение происходит по строкам, начинающимся с некого количества эмоджи/символов,
    затем слову "Диалог" и номера (например, "🔹Диалог 1 — ...", "⭐Диалог 2 — ...").
    """
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    text = "\n".join(full_text)

    # Используем регулярное выражение с мультистроковым режимом.
    # Шаблон: начало строки (с флагом MULTILINE), допускаем несловесные символы, затем "Диалог" и число.
    dialogues_raw = re.split(r"(?m)(?=^(?:\W+)?Диалог\s*\d+)", text)
    dialogues = []
    for d in dialogues_raw:
        d = d.strip()
        if d:
            processed = process_dialogue(d)
            if processed:
                dialogues.append(processed)
    return dialogues

if __name__ == "__main__":
    input_file = "./short_tunning.docx"      # Путь к вашему Word‑файлу с диалогами (например, 53 диалога)
    output_file = "fine_tune_data.jsonl"       # Выходной файл для сохранения данных в формате JSONL

    dialogues = process_docx(input_file)
    with open(output_file, "w", encoding="utf-8") as fout:
        for dialogue in dialogues:
            fout.write(json.dumps(dialogue, ensure_ascii=False) + "\n")

    print(f"Обработано {len(dialogues)} диалогов и сохранено в {output_file}")
