
import os
import traceback

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from db import initialize_database
from modules.chat import create_chat, save_message
from modules.ai import generate_answer


load_dotenv(override=True)

app = Flask(__name__)

initialize_database()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "success",
        "message": "STUDENTS AI is running!"
    })


@app.route("/api/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True) or {}

    question = data.get("question", "").strip()
    chat_id = data.get("chat_id")

    # Get selected programme and year
    programme = data.get("programme", "B.Tech")
    year = data.get("year", "1st Year")

    if not question:
        return jsonify({
            "error": "Please enter a question."
        }), 400

    # Validate programme and year
    valid_options = {
        "B.Tech": ["1st Year", "2nd Year", "3rd Year", "4th Year"],
        "M.Tech": ["1st Year", "2nd Year"],
        "Ph.D": ["Research"]
    }

    if programme not in valid_options or year not in valid_options[programme]:
        return jsonify({
            "error": "Invalid programme or year selection."
        }), 400

    try:

        if not chat_id:
            chat_id = create_chat(question)

        save_message(chat_id, "user", question)

        # Generate answer using selected programme and year
        answer = generate_answer(
            question,
            programme,
            year
        )

        save_message(chat_id, "assistant", answer)

        return jsonify({
            "status": "success",
            "chat_id": chat_id,
            "programme": programme,
            "year": year,
            "answer": answer
        })

    except Exception as error:

        print("\n========== CHAT ERROR ==========")
        print("Error:", error)
        traceback.print_exc()
        print("================================\n")

        return jsonify({
            "status": "error",
            "error": str(error)
        }), 500


if __name__ == "__main__":

    print("STUDENTS AI is starting...")
    print("Groq API configured:", bool(os.getenv("GROQ_API_KEY")))
    print("Groq model:", os.getenv("GROQ_MODEL"))

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
