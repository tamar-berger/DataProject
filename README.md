# ColumbusPath — Country Recommendation App

A lightweight web app that recommends **one country** to visit based on your preferences and past ratings.  
Frontend collects inputs; backend runs a smart pipeline over a prepared dataset of 180+ countries stored in **SQLite**.

---

## Features
- Rate countries you’ve visited (1–5 ⭐) and set what matters: **budget, safety, English level, transport, health, culture, nature, tourism crowding**.
- Hybrid scoring: content-based + neighborhood effects.
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
