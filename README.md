# HireGuard

Stylometric analysis and detection of fraudulent online job postings in Kenya.
Final year project, Strathmore University.

## Project structure

```
HireGuard/
├── backend/            Flask API + ML pipeline + PostgreSQL models
├── frontend/           React (Vite) web interface
└── data-collection/    Scrapers, EMSCAD loader, and annotation guide
```

This mirrors the four-tier architecture from Chapter 4 (System Analysis and
Design): `frontend` is the Presentation Tier, `backend/app/routes.py` is the
Application Tier, `backend/app/ml/` is the Machine Learning Tier, and
PostgreSQL (configured via `backend/.env`) is the Data Tier.

## Status

| Component | Status |
|---|---|
| Data collection (EMSCAD, BrighterMonday) | Working -- see `data-collection/README.md` |
| Data collection (Fuzu) | Scraper written, not yet tested against the live site |
| Backend API (`/api/classify`, `/api/history`) | Scaffolded and tested end-to-end in **stub mode** (no trained model yet) |
| Database schema | Defined (`backend/app/db/models.py`), not yet created in a real PostgreSQL instance |
| Frontend (submission, results, history pages) | Scaffolded, builds cleanly, not yet connected to a running backend |
| Trained Random Forest model + SHAP explainer | Not yet built -- this is the next major phase (Section 3.2.3) |

## Getting started

### 1. Backend

```
cd backend
pip install -r requirements.txt
cp .env.example .env        # edit DATABASE_URL once you have a Postgres instance
python init_db.py           # creates the 5 tables
python run.py                # starts the Flask API on :5000
```

Until a trained model exists at `backend/app/ml/artifacts/random_forest_model.joblib`,
the `/api/classify` endpoint runs in **stub mode**: it uses a simple
free-email + urgency-language heuristic instead of the real classifier, so
you can build and test the rest of the system (routes, database, frontend)
before training finishes. The API response includes `"is_stub_model": true`
whenever this is happening, and the frontend surfaces a visible notice when
it sees that flag.

### 2. Frontend

```
cd frontend
npm install
cp .env.example .env         # defaults to http://localhost:5000/api, change if needed
npm run dev                  # starts the Vite dev server, usually on :5173
```

### 3. Data collection

See `data-collection/README.md` -- this already has a working EMSCAD
pipeline and a tested BrighterMonday scraper.

## Next steps

1. Finish labeling the scraped BrighterMonday/Fuzu data (see
   `data-collection/labeling/annotation_guide.md`).
2. Combine EMSCAD + labeled BrighterMonday/Fuzu data into one dataset.
3. Build the stylometric feature extraction pipeline properly (the version
   in `backend/app/ml/feature_extractor.py` is a working first pass --
   swap in `textstat` for real Flesch-Kincaid/Gunning Fog once installed).
4. Train the Random Forest classifier + fit the SHAP TreeExplainer (Colab
   is a good place for this -- see Section 3.2.3 of the proposal).
5. Drop the resulting `.joblib` files into `backend/app/ml/artifacts/` --
   the API will automatically switch out of stub mode once they're there.
6. Set up a real PostgreSQL instance (local or hosted) and run `init_db.py`.
