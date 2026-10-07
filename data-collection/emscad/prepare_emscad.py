"""
Load the raw EMSCAD dataset and map it onto HireGuard's unified schema
(common/config.py) so it can be concatenated with the BrighterMonday and
Fuzu scrapes for the exploratory stylometric analysis (Section 3.2.1).

The raw file (data/raw/emscad_raw.csv) was pulled from a verified public
mirror of the Employment Scam Aegean Dataset (Vidros et al., 2017): 17,880
rows, 18 columns, 866 fraudulent / 17,014 legitimate -- matching the
published figures cited in the proposal (Section 1.1, 1.5).

Original EMSCAD source: http://emscad.samos.aegean.gr/
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.text_utils import clean_html, extract_email_domain, is_free_email_provider
from common.config import UNIFIED_COLUMNS

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "emscad_raw.csv"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "emscad_processed.csv"


def load_and_standardize(raw_path: Path = RAW_PATH) -> pd.DataFrame:
    df = pd.read_csv(raw_path)

    out = pd.DataFrame(index=df.index)
    out["source_id"] = df["job_id"]
    out["source"] = "emscad"
    out["title"] = df["title"].fillna("")
    out["location"] = df["location"].fillna("")
    out["department"] = df["department"].fillna("")
    out["salary_range"] = df["salary_range"].fillna("")

    for col in ["company_profile", "description", "requirements", "benefits"]:
        out[col] = df[col].fillna("").apply(clean_html)

    out["employment_type"] = df["employment_type"].fillna("")
    out["required_experience"] = df["required_experience"].fillna("")
    out["required_education"] = df["required_education"].fillna("")
    out["industry"] = df["industry"].fillna("")
    out["function"] = df["function"].fillna("")
    out["telecommuting"] = df["telecommuting"]
    out["has_company_logo"] = df["has_company_logo"]
    out["has_questions"] = df["has_questions"]

    combined_text = (
        out["company_profile"] + " " + out["description"] + " " + out["requirements"]
    )
    out["contact_email"] = ""
    out["contact_email_domain"] = combined_text.apply(extract_email_domain).fillna("")
    out["is_free_email_provider"] = out["contact_email_domain"].apply(
        lambda d: int(is_free_email_provider(d))
    )

    out["posted_date"] = ""
    out["url"] = ""
    out["scraped_at"] = ""
    out["fraudulent"] = df["fraudulent"]

    out = out[UNIFIED_COLUMNS]
    return out


if __name__ == "__main__":
    df = load_and_standardize()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    print(f"Processed {len(df):,} EMSCAD rows -> {OUT_PATH}")
    print(df["fraudulent"].value_counts().rename({0: "legitimate", 1: "fraudulent"}))
    print(f"\nRows with an email domain detected: {(df['contact_email_domain'] != '').sum():,}")
    print(f"Rows flagged as free email provider: {df['is_free_email_provider'].sum():,}")
