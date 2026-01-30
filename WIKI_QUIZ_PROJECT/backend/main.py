from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import openai
import json

# --------------- CONFIG ---------------
openai.api_key = "YOUR_OPENAI_API_KEY"  # <-- replace with your OpenAI key

# --------------- APP ---------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

history = []  # store past quizzes in-memory

# --------------- ROUTES ---------------
@app.get("/")
def home():
    return {"message": "Wiki Quiz API running"}

@app.get("/generate")
def generate(url: str = Query(..., description="Wikipedia article URL")):
    try:
        # --- Scrape Wikipedia ---
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        title_tag = soup.find("h1")
        title = title_tag.text if title_tag else "No title found"

        paragraphs = soup.find_all("p")
        summary = " ".join(p.text.strip() for p in paragraphs[:5])

        # --- Generate quiz using OpenAI GPT ---
        prompt = f"""
        Create 5 quiz questions from this Wikipedia article:
        Title: {title}
        Content: {summary}

        For each question, provide:
        1. Question
        2. Four options (A-D)
        3. Correct answer
        4. Short explanation
        5. Difficulty (easy, medium, hard)

        Return the result as strict JSON like this:
        {{
            "quiz": [
                {{"question": "...", "options": ["A","B","C","D"], "answer": "...", "explanation": "...", "difficulty": "easy"}},
                ...
            ],
            "related_topics": ["..."]
        }}
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1200
        )

        result_text = response.choices[0].message.content

        try:
            quiz_data = json.loads(result_text)
        except:
            quiz_data = {"quiz": [], "related_topics": []}

        result = {
            "url": url,
            "title": title,
            "summary": summary,
            "quiz": quiz_data.get("quiz", []),
            "related_topics": quiz_data.get("related_topics", [])
        }

        # Save to history
        history.append(result)
        return result

    except Exception as e:
        return {"error": str(e)}

@app.get("/history")
def get_history():
    return history
