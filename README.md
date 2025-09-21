# ColumbusPath — Country Recommendation App

A lightweight web app that recommends a single country to visit based on your preferences and past ratings.  
The Frontend collects the inputs while the backend runs a smart pipeline over a prepared dataset of 180+ countries stored in SQLite. 

**Link to website**: https://dataproject-68ch.onrender.com/

(It might take a few minutes for the servers to load after a long period of inactivity)

---

## How to use the website?
- Start by helping us get to know you. Choose countries that you have visited in the past and enjoyed. the more the merrier! 
- Rate the countries you’ve visited (On a scale from 1 to 5)
- Set what matters for you the most in the coming trip: **budget, safety, English level, transport, health, culture, nature, tourism crowding**. No need to rate all of them, only the most important ones.
- Press "See My Recommendation" and go buy the tickets :)

**Important Notes:**
- Our algorithm is designed to be positive. It gives more weight to places you liked in the past but it doesn't reduce weight from places you didn't. We believe people change and you might discover the potential in the future. 
- We use a hybrid scoring method that combines content-based and neighborhood-based recommendations.
- There is constraint filtering (e.g., high safety) with intelligent relaxation so you always get a result.

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
- `404 {"error":"No recommendations found"}` // Where nothing close enough was found
- `400 {"error":"<message>"}` // Any other unexpected error

---

## Data Sources (preprocessed)
- Safety, Health-care quality, Cost of living,  
  English proficiency, Cultural accessibility, Public transport,  
  International tourism arrivals, Natural & environmental spaces.  
See `pre_process/**/readme.md` for details.
