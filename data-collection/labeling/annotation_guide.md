# HireGuard: Manual Annotation Guide for Kenyan Job Postings

Used to label `fraudulent` (1) vs `legitimate` (0) for postings scraped from
BrighterMonday Kenya and Fuzu Kenya, before they're combined with EMSCAD.
Directly implements the annotation criteria from the proposal, Section
3.2.1: *"requests for personal financial information, absence of verifiable
company details, unrealistic compensation claims, and presence of free
email provider addresses in place of corporate domains."*

## How to label a posting

Read the full posting (title, company profile, description, requirements,
benefits) and check each indicator below. **A posting doesn't need every
red flag to be fraudulent** -- per Taneja et al. (2025), structural and
linguistic red flags tend to *compound*, so two or more moderate signals
together often outweigh one strong signal alone. Use judgement; log which
indicators fired in the `notes` column so the reasoning is auditable later.

| # | Indicator | What to look for |
|---|-----------|-------------------|
| 1 | Requests for financial/personal info | Asks for M-Pesa payment, "registration fee," ID/passport number, bank details, or payment for training/equipment *before* any interview |
| 2 | Absence of verifiable company details | No company name, generic/anonymous employer, no physical address, no verifiable website |
| 3 | Unrealistic compensation | Salary far above market rate for the stated role/experience level, or vague "attractive salary" with no range |
| 4 | Free email provider | Contact email uses gmail.com / yahoo.com / etc. instead of a corporate domain (see `is_free_email_provider` column -- already flagged automatically). Only emails written in the job text itself are detected; site template addresses (e.g. BrighterMonday's `anonymous@anonymous.com` placeholder) are excluded. |
| 5 | Urgency / over-promising language | "URGENT HIRING," "guaranteed income," "no experience needed," excessive exclamation marks |
| 6 | Vague job description | Generic duties with no specifics about the role, team, or responsibilities |
| 7 | Cyrillic/homoglyph substitution | Company name, email, or URL uses look-alike characters (already normalized in `contact_email_domain`, but re-check the raw `description` field manually) |

## Suggested labeling workflow

1. Run `python labeling/prepare_annotation.py` (from `data-collection/`).
   It combines both scrapes into `data/processed/annotation_batch.csv`,
   removes word-for-word duplicate descriptions, and shuffles the rows. It
   refuses to overwrite an existing batch, so your labels are safe.
2. Open that file in a spreadsheet and fill in `fraudulent` (0/1) and
   `notes` (which indicator numbers fired, e.g. "1,4,5"). Helper columns:
   `urgency_terms` (hint for indicator 5), `short_text` (description under
   200 characters -- consider excluding), `duplicate_count` (how many
   identical copies were collapsed into the row). Save as CSV (UTF-8).
3. Two annotators should independently label a sample (aim for 100+
   postings per source to start) and reconcile disagreements -- this gives
   you an inter-annotator agreement figure worth reporting in your
   methodology chapter.
4. Because genuinely fraudulent postings are rare on legitimate platforms
   like BrighterMonday and Fuzu, expect heavy class imbalance in the
   locally-scraped data (proposal Section 1.7.1) -- this is expected and is
   exactly why the proposal plans synthetic fraudulent samples and SMOTE
   (Section 3.2.2) to supplement real examples.

## A note on synthetic fraudulent examples

Since real fraudulent postings will be scarce in your scrape, Section
1.7.1 of the proposal anticipates generating synthetic fraudulent samples
based on the indicators above. When you're ready to build those, base each
synthetic posting on 2-3 of the indicators combined (not all 7 at once --
real fraud is rarely that obvious) so the classifier learns realistic
patterns rather than a caricature.
