
import os
from groq import Groq
from rag import search_regulations


def generate_answer(question):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("Groq API key is missing in .env")

    # Search official regulation PDFs
    results = search_regulations(question, top_k=5)

    if not results:
        return (
            "I could not find relevant information in the "
            "available official regulations. Please contact "
            "your HoD or Dean (Academic Courses) for clarification."
        )

    context = ""

    for item in results:
        context += (
            f"\nDocument: {item['document']}\n"
            f"PDF Page: {item['page']}\n"
            f"Content:\n{item['text']}\n"
            f"{'-' * 40}\n"
        )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile"
        ),
        messages=[
            {
                "role": "system",
                "content": """
You are STUDENTS AI, the official college regulations assistant.

STRICT RULES:
1. Answer only using the provided regulation context.
2. Never invent rules, percentages, dates or clauses.
3. If the context does not contain the answer, clearly say
   that the information could not be verified.
4. Mention the document name and PDF page number.
5. Mention clause numbers only when they appear in the context.
6. Reply in the same language as the student's question:
   English, Tamil or Tanglish.
7. Keep answers clear and student-friendly.
"""
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Official Regulation Context:\n{context}"
                )
            }
        ],
        temperature=0.1
    )

    return response.choices[0].message.content
