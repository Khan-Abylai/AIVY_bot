#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import logging
import argparse
import json
import random
from pathlib import Path
from config import OPENAI_API_KEY, TRAIN_JSONL
from openai import OpenAI

# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
# -------------------------------------------------------------------

def split_dataset(path: Path, valid_ratio: float = 0.1) -> (Path, Path, int):
    """
    Split the JSONL dataset into training and validation files.
    Returns paths to (train_file, valid_file) and total examples.
    """
    lines = [l for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
    total = len(lines)
    if total < 2:
        logger.error("Not enough examples (%d) to split.", total)
        sys.exit(1)
    random.shuffle(lines)
    split_idx = max(1, int(total * (1 - valid_ratio)))
    train_lines = lines[:split_idx]
    valid_lines = lines[split_idx:]

    base = path.with_suffix('')
    train_path = base.with_name(f"{base.name}_train.jsonl")
    valid_path = base.with_name(f"{base.name}_valid.jsonl")
    train_path.write_text("\n".join(train_lines) + "\n", encoding='utf-8')
    valid_path.write_text("\n".join(valid_lines) + "\n", encoding='utf-8')

    logger.info("Dataset split: %d train / %d valid (%.1f%% valid)",
                 len(train_lines), len(valid_lines), len(valid_lines) / total * 100)
    return train_path, valid_path, total


def upload_file(client: OpenAI, path: Path, purpose: str = "fine-tune") -> str:
    logger.info("Uploading file (%s): %s", purpose, path)
    resp = client.files.create(
        file=open(path, "rb"),
        purpose=purpose
    )
    logger.info("Uploaded: %s -> %s", purpose, resp.id)
    return resp.id


def start_fine_tune(
    client: OpenAI,
    train_id: str,
    valid_id: str,
    base_model: str,
    n_epochs: int,
    lr_mult: float,
    batch_size: int,
    suffix: str
) -> str:
    logger.info(
        "Starting fine‑tune: model=%s epochs=%d lr=%.4f batch=%d suffix=%s",
        base_model, n_epochs, lr_mult, batch_size, suffix
    )
    job = client.fine_tuning.jobs.create(
        training_file=train_id,
        validation_file=valid_id,
        model=base_model,
        hyperparameters={
            "n_epochs": n_epochs,
            "learning_rate_multiplier": lr_mult,
            "batch_size": batch_size
        },
        suffix=suffix
    )
    logger.info("Job ID: %s", job.id)
    return job.id


def poll_job(client: OpenAI, job_id: str, interval: int) -> dict:
    logger.info("Polling job %s every %ds", job_id, interval)
    while True:
        job = client.fine_tuning.jobs.retrieve(job_id)
        logger.info("Status: %s", job.status)
        if job.status in ("succeeded", "failed"):
            return job
        time.sleep(interval)


def adjust_hyperparams(total: int, epochs: int, lr: float, batch: int):
    """
    Adjust hyperparameters based on dataset size.
    - Large dataset (>100): reduce lr, increase batch.
    - Small dataset (<30): increase epochs.
    """
    if total >= 100:
        lr = min(lr, 0.03)
        batch = max(batch, 16)
    elif total <= 30:
        epochs = max(epochs, epochs * 2)
    return epochs, lr, batch


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune a chat model with dynamic hyperparams and dataset split"
    )
    parser.add_argument("--model",      default="gpt-3.5-turbo-1106")
    parser.add_argument("--epochs",     type=int,   default=6)
    parser.add_argument("--lr",         type=float, default=0.05)
    parser.add_argument("--batch-size", type=int,   default=8)
    parser.add_argument("--suffix",     default="aivi-psybot-maxqc")
    parser.add_argument("--poll-interval", type=int, default=30)
    parser.add_argument("--valid-ratio", type=float, default=0.1,
                        help="Validation split ratio (0-1)")
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not set")
        sys.exit(1)

    train_path = Path(TRAIN_JSONL)
    if not train_path.exists():
        logger.error("Train file not found: %s", train_path)
        sys.exit(1)

    # Split dataset
    train_file, valid_file, total = split_dataset(train_path, args.valid_ratio)

    # Adjust hyperparameters
    epochs, lr, batch = adjust_hyperparams(total, args.epochs, args.lr, args.batch_size)
    logger.info("Using hyperparams -> epochs: %d, lr: %.4f, batch: %d", epochs, lr, batch)

    # Initialize client
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Upload files
    train_id = upload_file(client, train_file, purpose="fine-tune")
    valid_id = upload_file(client, valid_file, purpose="fine-tune")

    # Start fine-tuning
    job_id = start_fine_tune(
        client, train_id, valid_id,
        args.model, epochs, lr, batch,
        args.suffix
    )

    # Poll until done
    job = poll_job(client, job_id, args.poll_interval)

    # Report
    if job.status == "succeeded":
        logger.info("✅ Fine‑tune succeeded: %s", job.fine_tuned_model)
        print(job.fine_tuned_model)
    else:
        logger.error("❌ Fine‑tune failed: %s", job)
        sys.exit(1)


if __name__ == "__main__":
    main()
