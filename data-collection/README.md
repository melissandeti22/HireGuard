# HireGuard -- Data Collection

Implements Section 3.2.1 (Data Acquisition) of the HireGuard proposal:
EMSCAD as the base dataset, supplemented by scraped Kenyan job postings
from BrighterMonday Kenya and Fuzu Kenya.

## Status

| Component | Status |
|---|---|
| EMSCAD download + standardization | **Done, tested.** 17,880 rows loaded, class split (17,014 legit / 866 fraudulent) matches the published dataset exactly. |
| BrighterMonday scraper | Written, **not yet run against the live site** -- see note below. |
| Fuzu scraper | Written, **not yet run against the live site** -- see note below. |
| Manual annotation guide | Done -- see `labeling/annotation_guide.md`. |

## Important: run the scrapers from your own machine

This was built in a sandboxed environment whose outbound network only
reaches package registries (PyPI, npm, GitHub) -- not brightermonday.co.ke
or fuzu.com. So the two scrapers were written against the *confirmed* live
page structure and URL patterns (checked via search/fetch while building
this), but could not be executed end-to-end here. Before you rely on them:

1. `pip install -r requirements.txt`
2. Run a small test: `python scrapers/brightermonday_scraper.py --max-pages 1`
3. Open the output CSV and check the `title`, `company_profile`, and
   `description` fields look right.
4. If BrighterMonday or Fuzu have changed their page markup, the fix is
   almost always in the `SELECTORS` dict at the top of the scraper file --
   open a job listing in your browser, right-click → Inspect, and update
   the CSS selector that's no longer matching.
5. Once a test run looks right, scale up `--max-pages` (BrighterMonday had
   ~122 pages / ~1,940 jobs at 16/page when this was checked; Fuzu's job
   count fluctuates similarly).

Both scrapers currently pull the *whole* cleaned page body into
`description` rather than splitting it into separate requirements/benefits
fields, since that split depends on markup I couldn't inspect directly.
That's a reasonable v1 -- your stylometric features (Section 3.2.2) mostly
operate on the combined text anyway -- but if you want the fields split
cleanly, inspect a live detail page and add the extra selectors.

## Structure

```
hireguard_data_collection/
├── common/
│   ├── config.py         # unified schema, free-email list, request settings
│   ├── http_client.py    # rate-limited session, robots.txt compliance, retries
│   └── text_utils.py     # HTML cleaning, email/domain extraction, Cyrillic normalization
├── scrapers/
│   ├── brightermonday_scraper.py
│   └── fuzu_scraper.py
├── emscad/
│   └── prepare_emscad.py # loads + standardizes the EMSCAD CSV (tested, working)
├── labeling/
│   └── annotation_guide.md
└── data/
    ├── raw/               # emscad_raw.csv is here already; scraper output goes here too
    └── processed/         # emscad_processed.csv (standardized, ready to concatenate)
```

## Ethics / compliance notes

- Both scrapers check `robots.txt` before fetching anything and will
  refuse to crawl disallowed paths (fails closed if robots.txt can't be
  read at all).
- Default rate limit is 1 request per 3 seconds -- deliberately slow so the
  scrape doesn't look like an attack and doesn't burden either site.
- Only publicly viewable job listing text is collected. No login-gated
  content, no personal candidate data. This matches Section 3.2.1's
  commitment that "no personally identifiable information will be
  retained from scraped postings beyond the text fields required for
  stylometric analysis."
- Worth a quick read of BrighterMonday's and Fuzu's Terms of Service
  before a large-scale crawl -- scraping publicly visible pages at a
  polite rate for academic research is common practice, but you'll want
  that check on record for your methodology write-up.

## Next step

Once both scrapes and manual labeling are done, concatenate
`data/processed/emscad_processed.csv` with the labeled BrighterMonday and
Fuzu CSVs into one dataframe -- all three already share the same column
schema (`common/config.py: UNIFIED_COLUMNS`) -- and you're ready to move
into the stylometric feature extraction pipeline (Section 3.2.2).
