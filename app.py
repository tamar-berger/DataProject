from flask import Flask, render_template, request, Response, jsonify
from pre_process.all_countries_dict import COUNTRIES_MAP

app = Flask(__name__)

# Optional hard limit for demo payload size
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024  # 256KB

# Build a clean display list for the UI, stable order
COUNTRIES = sorted(set(COUNTRIES_MAP.values()))

@app.get("/")
def index():
    return render_template("index.html", countries=COUNTRIES)


@app.post("/api/recommend")
def recommend():
    """
    Stub that returns plain text with a country name.
    Expecting JSON like:
    {
      "ratings": {"Spain": 5, "Italy": 4},
      "weights": {"budget": 80, "safety": 60, "english": 40}
    }
    Replace this with your real backend logic or call out to your service.
    """
    try:
        data = request.get_json(force=True) or {}
        ratings = data.get("ratings", {})           # dict of {country: 1..5}
        weights = data.get("weights", {})           # dict of {criterion: 0..100}

        # Very light demo logic,
        # pick a country not rated yet and pretend it matches the highest weight
        pool = [c for c in COUNTRIES if c not in ratings] or COUNTRIES[:]
        # tie breaker by alphabetical order so results are deterministic
        _ = max(weights, key=weights.get) if weights else "budget"  # not used in stub
        suggestion = sorted(pool)[0]

        # Return plain text because the client expects text
        return Response(suggestion, mimetype="text/plain")
    except Exception as e:
        # Fallback to JSON error if something goes wrong
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)