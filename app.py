from flask import Flask, render_template, request, Response, jsonify

app = Flask(__name__)

# Simple list for the demo UI, replace or load dynamically if you prefer
COUNTRIES = [
    "Portugal","Spain","Italy","France","Greece","Netherlands","Germany",
    "United Kingdom","Ireland","Switzerland","Austria","Croatia","Turkey",
    "Japan","South Korea","Thailand","Vietnam","Singapore","Malaysia",
    "United States","Canada","Mexico","Brazil","Argentina","Chile",
    "Australia","New Zealand","Morocco","Egypt","South Africa","Kenya",
    "United Arab Emirates","Israel","Jordan","Georgia"
]

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
        print(data)

        # Very light demo logic,
        # pick a country not rated yet and pretend it matches the highest weight
        pool = [c for c in COUNTRIES if c not in ratings] or COUNTRIES[:]
        # tie breaker by alphabetical order so results are deterministic
        top_key = max(weights, key=weights.get) if weights else "budget"
        suggestion = sorted(pool)[0]

        # Return plain text because you said your backend will do that
        return Response(suggestion, mimetype="text/plain")
    except Exception as e:
        # Fallback to JSON error if something goes wrong
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)
