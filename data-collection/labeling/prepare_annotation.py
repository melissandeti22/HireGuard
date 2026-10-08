"""
Build a single annotation file from the BrighterMonday and Fuzu scrapes,
ready to label in a spreadsheet following labeling/annotation_guide.md.

- Removes postings whose description duplicates another's word for word
  (employers often post one ad per branch). Duplicates would otherwise end
  up on both sides of a train/test split and inflate evaluation scores.
  `duplicate_count` records how many copies were collapsed into each row.
- Flags descriptions under SHORT_TEXT_CHARS characters (`short_text` = 1):
  too little text for reliable stylometric features. Kept, not dropped --
  decide during annotation.
- Adds `urgency_terms` (count of URGENCY_OVERPROMISE_TERMS) as a hint for
  indicator 5; `is_free_email_provider` already covers indicator 4.
- Adds an empty `notes` column for the indicator numbers that fired.
- Shuffles rows (fixed seed) so annotators don't label one source in a block.

Usage (from data-collection/):
    python labeling/prepare_annotation.py
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import UNIFIED_COLUMNS, URGENCY_OVERPROMISE_TERMS

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_INPUTS = [DATA_DIR / "raw" / "brightermonday_raw.csv", DATA_DIR / "raw" / "fuzu_raw.csv"]
DEFAULT_OUTPUT = DATA_DIR / "processed" / "annotation_batch.csv"
SHORT_TEXT_CHARS = 200
SEED = 42

ANNOTATION_COLUMNS = ["duplicate_count", "short_text", "urgency_terms", "notes"]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def count_urgency_terms(text: str) -> int:
    lowered = text.lower()
    return sum(lowered.count(term) for term in URGENCY_OVERPROMISE_TERMS)


def build(inputs: list[Path]) -> tuple[pd.DataFrame, dict]:
    frames = [pd.read_csv(p, dtype=str).fillna("") for p in inputs if p.exists()]
    if not frames:
        raise SystemExit(f"No input files found: {', '.join(map(str, inputs))}")
    df = pd.concat(frames, ignore_index=True)

    stats = {"input_rows": len(df), "by_source_in": df["source"].value_counts().to_dict()}

    df = df[df["description"].str.strip() != ""]
    key = df["description"].map(normalize)
    df = df.assign(duplicate_count=key.map(key.value_counts()))
    df = df[~key.duplicated(keep="first")]

    df["short_text"] = (df["description"].str.len() < SHORT_TEXT_CHARS).astype(int)
    df["urgency_terms"] = df["description"].map(count_urgency_terms)
    df["notes"] = ""

    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    df = df[UNIFIED_COLUMNS + ANNOTATION_COLUMNS]

    stats.update({
        "output_rows": len(df),
        "by_source_out": df["source"].value_counts().to_dict(),
        "duplicates_removed": stats["input_rows"] - len(df),
        "short_text": int(df["short_text"].sum()),
        "free_email": int((df["is_free_email_provider"] == "1").sum()),
        "with_urgency_terms": int((df["urgency_terms"] > 0).sum()),
    })
    return df, stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare a deduplicated annotation file.")
    parser.add_argument("--inputs", nargs="+", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true",
                        help="Overwrite the output file if it exists (it may contain your labels).")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        raise SystemExit(
            f"{args.output} already exists and may contain annotations. "
            f"Pass --force to overwrite it, or choose another --output."
        )

    df, stats = build(args.inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel detects the encoding (bullets, accented names) on open.
    df.to_csv(args.output, index=False, encoding="utf-8-sig")

    print(f"Read {stats['input_rows']:,} rows {stats['by_source_in']}")
    print(f"Removed {stats['duplicates_removed']:,} duplicate/empty descriptions")
    print(f"Wrote {stats['output_rows']:,} rows {stats['by_source_out']} -> {args.output}")
    print(f"  short_text (<{SHORT_TEXT_CHARS} chars): {stats['short_text']}")
    print(f"  free email provider:        {stats['free_email']}")
    print(f"  with urgency terms:         {stats['with_urgency_terms']}")
