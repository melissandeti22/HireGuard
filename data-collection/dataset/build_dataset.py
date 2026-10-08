"""
Combine EMSCAD with the manually labelled BrighterMonday/Fuzu postings into
one training dataset with a leakage-safe train/test split, ready to upload
to Colab for feature extraction, Random Forest training and SHAP.

What it does
- Loads data/processed/emscad_processed.csv (labels from the dataset) and the
  verified annotation file (labels from the `fraudulent` column you filled in).
  Rows you have not labelled yet are left out.
- Builds a single `text` field from title + description + requirements +
  benefits -- the posting body the backend's FeatureExtractor sees.
  company_profile is deliberately NOT included: in EMSCAD it is a paragraph
  that is missing for 68% of fraudulent vs 16% of legitimate postings, while
  in the scrapes it is only the employer's name. Including it would let the
  model learn the data source instead of writing style. It is kept as a
  separate column for analysis.
- Drops postings whose text is shorter than --min-chars (too little text for
  stylometric features).
- Removes duplicate texts across both sources. Duplicate groups with
  conflicting labels are dropped entirely and reported.
- Assigns each posting to a group (employer, else contact domain, else the
  posting itself) and makes a stratified, group-aware train/test split, so the
  same employer's ads never appear on both sides -- otherwise near-identical
  ads (e.g. one per branch) inflate test scores.

Usage (from data-collection/):
    python dataset/build_dataset.py
    python dataset/build_dataset.py --labelled data/processed/annotation_batch_prelabelled.csv

--use-suggested fills unlabelled rows from the AI `suggested_label` column.
Use it only to test the pipeline end to end: those rows are marked
label_source = "ai_suggested" and must not be reported as manual labels.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_EMSCAD = DATA_DIR / "processed" / "emscad_processed.csv"
DEFAULT_LABELLED = DATA_DIR / "processed" / "annotation_batch_prelabelled.csv"
DEFAULT_OUTPUT = DATA_DIR / "processed" / "hireguard_dataset.csv"
TEXT_FIELDS = ["title", "description", "requirements", "benefits"]
ANONYMOUS = {"", "anonymous employer", "confidential", "-"}
SEED = 42

OUTPUT_COLUMNS = [
    "id", "source", "label_source", "fraudulent", "split", "group", "text", "text_chars",
    "title", "company_profile", "location", "salary_range", "employment_type",
    "contact_email_domain", "is_free_email_provider", "url",
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def build_text(df: pd.DataFrame) -> pd.Series:
    parts = df[TEXT_FIELDS].apply(lambda col: col.str.strip())
    return parts.apply(lambda row: "\n".join(p for p in row if p), axis=1)


def group_key(row: pd.Series) -> str:
    """Employer name (scrapes) or company profile (EMSCAD), else email domain, else the posting."""
    company = normalize(row["company_profile"])
    if company not in ANONYMOUS:
        return f"{row['source']}:co:{short_hash(company)}"
    domain = row["contact_email_domain"].strip().lower()
    if domain and row["is_free_email_provider"] != "1":
        return f"dom:{domain}"
    return f"{row['source']}:post:{short_hash(row['text_norm'])}"


def load_emscad(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    df["label_source"] = "emscad"
    return df


def load_labelled(path: Path, use_suggested: bool) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    df["fraudulent"] = df["fraudulent"].str.strip()
    stats = {"rows": len(df), "manual": int(df["fraudulent"].isin(["0", "1"]).sum())}

    df["label_source"] = "manual"
    if use_suggested and "suggested_label" in df.columns:
        fill = ~df["fraudulent"].isin(["0", "1"]) & df["suggested_label"].isin(["0", "1"])
        df.loc[fill, "fraudulent"] = df.loc[fill, "suggested_label"]
        df.loc[fill, "label_source"] = "ai_suggested"
        stats["ai_suggested"] = int(fill.sum())

    unlabelled = ~df["fraudulent"].isin(["0", "1"])
    stats["unlabelled_dropped"] = int(unlabelled.sum())
    return df[~unlabelled].copy(), stats


def build(args) -> pd.DataFrame:
    emscad = load_emscad(args.emscad)
    local, local_stats = load_labelled(args.labelled, args.use_suggested)
    print(f"EMSCAD: {len(emscad):,} rows | local file: {local_stats}")

    df = pd.concat([emscad, local], ignore_index=True)
    df = df[df["fraudulent"].isin(["0", "1"])].copy()
    df["text"] = build_text(df)
    df["text_chars"] = df["text"].str.len()
    df["text_norm"] = df["text"].map(normalize)

    short = df["text_chars"] < args.min_chars
    print(f"Dropped {short.sum():,} postings under {args.min_chars} chars")
    df = df[~short]

    # Duplicates: keep one per text; drop whole groups whose labels disagree.
    label_sets = df.groupby("text_norm")["fraudulent"].nunique()
    conflicting = df["text_norm"].isin(label_sets[label_sets > 1].index)
    if conflicting.any():
        print(f"Dropped {conflicting.sum()} rows: identical text with conflicting labels")
    df = df[~conflicting]
    before = len(df)
    df = df.drop_duplicates("text_norm", keep="first")
    print(f"Removed {before - len(df):,} duplicate texts")

    df["group"] = df.apply(group_key, axis=1)
    df["id"] = df["source"] + ":" + df["source_id"].where(df["source_id"] != "", df["text_norm"].map(short_hash))

    y = df["fraudulent"].astype(int).to_numpy()
    n_splits = round(1 / args.test_size)
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    _, test_idx = next(cv.split(df, y, groups=df["group"]))
    df["split"] = "train"
    df.iloc[test_idx, df.columns.get_loc("split")] = "test"

    overlap = set(df.loc[df.split == "train", "group"]) & set(df.loc[df.split == "test", "group"])
    assert not overlap, f"{len(overlap)} groups appear in both splits"
    return df[OUTPUT_COLUMNS].reset_index(drop=True)


def summarize(df: pd.DataFrame) -> None:
    table = pd.crosstab([df["source"], df["split"]], df["fraudulent"], margins=True)
    table.columns = [{"0": "legitimate", "1": "fraudulent"}.get(c, c) for c in table.columns]
    print("\n" + table.to_string())
    for split in ("train", "test"):
        part = df[df.split == split]
        print(f"{split}: {len(part):,} rows, {part.fraudulent.astype(int).mean():.2%} fraudulent, "
              f"{part.group.nunique():,} groups")
    sources = df.label_source.value_counts().to_dict()
    print("label sources:", sources)
    if "ai_suggested" in sources:
        print("WARNING: dataset contains AI-suggested labels -- for pipeline testing only.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the combined HireGuard training dataset.")
    parser.add_argument("--emscad", type=Path, default=DEFAULT_EMSCAD)
    parser.add_argument("--labelled", type=Path, default=DEFAULT_LABELLED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-chars", type=int, default=200)
    parser.add_argument("--test-size", type=float, default=0.2, help="Approximate share of rows held out for testing.")
    parser.add_argument("--use-suggested", action="store_true",
                        help="Fill unlabelled rows from suggested_label (pipeline testing only).")
    args = parser.parse_args()

    for p in (args.emscad, args.labelled):
        if not p.exists():
            sys.exit(f"Input not found: {p}")

    dataset = build(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False, encoding="utf-8")
    summarize(dataset)
    print(f"\nWrote {len(dataset):,} rows -> {args.output}")
