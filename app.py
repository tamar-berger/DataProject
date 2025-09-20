from flask import Flask, render_template, request, Response, jsonify
import sqlite3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'algorithm'))
from main_recommender import SmartCountryRecommender

app = Flask(__name__)

# Optional hard limit for demo payload size
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024  # 256KB

# Get countries from database
def get_countries_from_db():
    """Get list of countries from the database"""
    try:
        conn = sqlite3.connect('country_rates.db')
        cursor = conn.execute("SELECT DISTINCT country_name FROM country_indicators ORDER BY country_name")
        countries = [row[0] for row in cursor.fetchall()]
        conn.close()
        return countries
    except Exception as e:
        print(f"Error loading countries from database: {e}")
        return []

# Build a clean display list for the UI, stable order
COUNTRIES = get_countries_from_db()

# Initialize the recommender system
recommender = SmartCountryRecommender()

@app.get("/")
def index():
    return render_template("index.html", countries=COUNTRIES)


@app.post("/api/recommend")
def recommend():
    """
    Generate country recommendations using the smart algorithm.
    Expecting JSON like:
    {
      "ratings": {"Spain": 5, "Italy": 4},
      "weights": {"budget": 80, "safety": 60, "english": 40}
    }
    """
    try:
        data = request.get_json(force=True) or {}
        ratings = data.get("ratings", {})           # dict of {country: 1..5}
        weights = data.get("weights", {})           # dict of {criterion: 0..100}

        # Map frontend weight names to algorithm preference names
        weight_mapping = {
            'budget': 'Budget friendliness',
            'safety': 'Safety level', 
            'english': 'English speaking level',
            'transport': 'Public transport access',
            'health': 'Health care quality',
            'culture': 'Culture accessibility rate',
            'nature': 'Nature and scenery',
            'tourism': 'Tourism crowd level'
        }
        
        # Convert weights to algorithm format
        importance_scores = {}
        for key, value in weights.items():
            if key in weight_mapping:
                importance_scores[weight_mapping[key]] = value

        # Call the algorithm
        recommendations, explanation_data = recommender.recommend_countries(
            importance_scores=importance_scores,
            user_ratings=ratings if ratings else None,
            num_recommendations=1  # Return only the top recommendation
        )
        
        if recommendations:
            # Return the top recommended country
            top_country = recommendations[0][0]
            return Response(top_country, mimetype="text/plain")
        else:
            # Fallback if no recommendations
            return jsonify({"error": "No recommendations found"}), 404

    except Exception as e:
        # Fallback to JSON error if something goes wrong
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True, port=5001)