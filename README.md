# ColumbusPath — Country Recommendation App

A lightweight web app that recommends **one country** to visit based on your preferences and past ratings.  
Frontend collects inputs; backend runs a smart pipeline over a prepared dataset of 180+ countries stored in **SQLite**.

---

## Features
- Rate countries you’ve visited (1–5 ⭐) and set what matters: **budget, safety, English level, transport, health, culture, nature, tourism crowding**.
- Hybrid scoring: content-based + neighborhood effects + popularity.
- Constraint filtering (e.g., high safety) with intelligent relaxation so you always get a result.
- Single “best next country” returned as plain text for easy UI use.

---

## Tech Stack
- **Backend:** Flask + gunicorn  
- **ML / Data:** pandas, scikit-learn, numpy  
- **Storage:** SQLite (`country_rates.db`)  
- **Frontend:** HTML/CSS/JS (vanilla)

---

## Repository Layout
```
final_project/
├─ app.py                    # Flask app (serves UI + /api/recommend)
├─ Procfile                  # Render: web process w/ gunicorn
├─ requirements.txt          # NOTE: no 'sqlite3' or 'typing' here
├─ country_rates.db          # SQLite database (prebuilt features)
├─ templates/
│  └─ index.html             # Single-page UI
├─ static/
│  ├─ styles.css
│  ├─ app.js                 # Calls /api/recommend
│  └─ media/                 # Assets (map/video/images)
├─ algorithm/
│  ├─ config.py              # DATABASE_PATH, hyperparameters, feature map
│  ├─ main_recommender.py    # Orchestrates full pipeline
│  ├─ 01_feature_engineering/...
│  ├─ 02_user_modeling/...
│  ├─ 03_scoring_engine/...
│  ├─ 04_constraint_filtering/...
│  └─ 05_diversification/...
└─ pre_process/              # Raw CSVs + mini readmes (data sources)
```

---

## Quickstart (Local)

1) **Python & venv**
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scriptsctivate
pip install -r requirements.txt
```

2) **Run**
```bash
# Option A: dev
python app.py

# Option B: prod-like
gunicorn -b 0.0.0.0:8000 app:app
```

3) Open: `http://localhost:5001` (dev) or `http://localhost:8000` (gunicorn).

> The app reads the DB path from `algorithm/config.py` (`DATABASE_PATH`).  
> The bundled DB is `final_project/country_rates.db`.

---

## API

**POST** `/api/recommend`  
Returns **text/plain** with the single recommended country.

**Request JSON**
```json
{
  "ratings": { "France": 5, "Italy": 4 }, 
  "weights": {
    "budget": 70, "safety": 85, "english": 60,
    "transport": 50, "health": 40, "culture": 80,
    "nature": 50, "tourism": 30
  }
}
```

**Response (200)**
```
Portugal
```

**Errors**
- `404 {"error":"No recommendations found"}`
- `400 {"error":"<message>"}`

---

## Data Sources (preprocessed)
- Safety/Crime (Numbeo indices), Health-care quality, Cost of living,  
  English proficiency (EF EPI), Cultural accessibility, Public transport,  
  International tourism arrivals, Natural & environmental spaces.  
See `pre_process/**/readme.md` for details.

---

## Deploy on Render (Web Service)

1) **Connect repo** → Create *Web Service*.  
2) **Build command:** `pip install -r requirements.txt`  
3) **Start command:** taken from `Procfile`  
   ```
   web: gunicorn -b 0.0.0.0:$PORT app:app
   ```
4) **Persistence options:**
   - For demo/POC you can ship `country_rates.db` in the repo (works but **not persistent** across rebuilds if you modify it at runtime).
   - For production: prefer **Render PostgreSQL** or attach a **Persistent Disk** and point `DATABASE_PATH` to that mount.

> **Do not add** `sqlite3` to `requirements.txt`. It is built-in with Python.

---

## Troubleshooting
- **Build fails: “No matching distribution for sqlite3”**  
  Remove `sqlite3` (and `typing`) from `requirements.txt`.
- **DB not found**: verify `algorithm/config.py::DATABASE_PATH` points to the shipped `country_rates.db` or to your mounted path.
- **Gunicorn + SQLite locks**: for real traffic use PostgreSQL; SQLite is OK for POC/single worker.

---

## License / Credits
Internal academic project (“ColumbusPath”) for travel recommendations using curated public datasets.  
© The authors. All rights reserved (adjust as needed).
