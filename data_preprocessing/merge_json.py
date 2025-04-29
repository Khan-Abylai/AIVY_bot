#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

def load_dialogues(path: Path) -> List[Dict[str, Any]]:
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a list, got {type(data).__name__}")
    return data

def reindex_and_merge(dialogues1: List[Dict[str, Any]],
                      dialogues2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = dialogues1 + dialogues2
    reindexed: List[Dict[str, Any]] = []
    for new_id, dlg in enumerate(merged, start=1):
        new_dlg = dict(dlg)
        new_dlg['dialogue_id'] = new_id
        reindexed.append(new_dlg)
    return reindexed

def save_dialogues(dialogues: List[Dict[str, Any]], path: Path) -> None:
    with path.open('w', encoding='utf-8') as f:
        json.dump(dialogues, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(
        description="Merge two JSON dialogue files and reindex dialogue_id sequentially."
    )
    parser.add_argument(
        'input1',
        type=Path,
        nargs='?',
        default=Path("aivi_dialogues_dataset_1.json"),
        help="Path to the first input JSON file (default: %(default)s)"
    )
    parser.add_argument(
        'input2',
        type=Path,
        nargs='?',
        default=Path("dataset_2.json"),
        help="Path to the second input JSON file (default: %(default)s)"
    )
    parser.add_argument(
        'output',
        type=Path,
        nargs='?',
        default=Path("aivi_dialogues_dataset_2.json"),
        help="Path for the merged output JSON file (default: %(default)s)"
    )
    args = parser.parse_args()

    dialogs1 = load_dialogues(args.input1)
    dialogs2 = load_dialogues(args.input2)
    merged = reindex_and_merge(dialogs1, dialogs2)
    save_dialogues(merged, args.output)

    print(f"Written {len(merged)} dialogues to {args.output}")

if __name__ == '__main__':
    main()
