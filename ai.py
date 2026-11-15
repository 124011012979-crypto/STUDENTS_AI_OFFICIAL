
import os
import re
import math
from pathlib import Path
from collections import Counter

from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_FOLDER = BASE_DIR / "data" / "regulations"

_document_chunks = []
_document_vectors = []
_idf = {}
_index_loaded = False


# --------------------------------------------------
# 1. PROGRAMME IDENTIFICATION
# --------------------------------------------------

def normalize_program(programme):

    if not programme:
        return None

    value = programme.lower().replace(" ", "").replace(".", "")

    if value == "btech":
        return "B.Tech"

    if value == "mtech":
        return "M.Tech"

    if value in ["phd", "phdprogramme"]:
        return "Ph.D."

    return None


def identify_program(filename):

    name = filename.lower()
    name = re.sub(r"[^a-z0-9]", "", name)

    if "mtech" in name:
        return "M.Tech"

    if "phd" in name:
        return "Ph.D."

    if "btech" in name:
        return "B.Tech"

    return "Unknown"


def detect_program(question):

    q = question.lower()

    if re.search(r"\bm\s*\.?\s*tech\b|\bmtech\b", q):
        return "M.Tech"

    if re.search(r"\bb\s*\.?\s*tech\b|\bbtech\b", q):
        return "B.Tech"

    if re.search(r"\bph\s*\.?\s*d\b|\bphd\b", q):
        return "Ph.D."

    return None


# --------------------------------------------------
# 2. TEXT PROCESSING
# --------------------------------------------------

def tokenize(text):

    words = re.findall(r"[a-zA-Z0-9]+", text.lower())

    tokens = list(words)

    for i in range(len(words) - 1):
        tokens.append(words[i] + "_" + words[i + 1])

    return tokens


def expand_question(question):

    q = question.lower()
    terms = []

    if any(word in q for word in [
        "attendance", "attendence", "absent",
        "shortage", "present", "72%", "75%"
    ]):
        terms.extend([
            "attendance", "75 percent", "75%",
            "65 percent", "65%", "examination",
            "end semester examination",
            "medical reasons", "hospitalization",
            "accident", "specific illness",
            "sports events", "prior permission",
            "Head of Department", "Dean FET",
            "exemption", "documents",
            "R7.3", "R7.4", "R7.5", "R7.6", "R7.7"
        ])

    if any(word in q for word in [
        "exam", "examination", "write exam",
        "appear", "eligibility", "eligible",
        "allow", "allowed", "permission"
    ]):
        terms.extend([
            "attendance", "75%", "65%",
            "examination eligibility",
            "end semester examination",
            "registration", "fee",
            "exemption", "medical",
            "sports", "prior permission",
            "R7.3", "R7.4", "R7.5", "R7.7"
        ])

    if any(word in q for word in ["credit", "credits"]):
        terms.extend([
            "total credits", "degree credits",
            "lecture", "tutorial", "practical",
            "laboratory", "internship",
            "industrial training", "semester",
            "online course"
        ])

    if any(word in q for word in [
        "medical", "sports", "exemption"
    ]):
        terms.extend([
            "65%", "75%", "attendance",
            "permission", "supporting documents",
            "Head of Department", "Dean FET"
        ])

    return question + " " + " ".join(terms)


# --------------------------------------------------
# 3. LOAD REGULATION PDFS
# --------------------------------------------------

def load_regulations():

    global _document_chunks
    global _document_vectors
    global _idf
    global _index_loaded

    if _index_loaded:
        return

    if not PDF_FOLDER.exists():
        raise FileNotFoundError(
            f"Regulations folder not found: {PDF_FOLDER}"
        )

    pdf_files = list(PDF_FOLDER.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(
            "No PDF files found inside data/regulations."
        )

    _document_chunks = []

    for pdf_path in pdf_files:

        program = identify_program(pdf_path.name)

        if program == "Unknown":
            print("Skipping unrecognized PDF:", pdf_path.name)
            continue

        try:

            reader = PdfReader(str(pdf_path))

            for page_number, page in enumerate(reader.pages, start=1):

                page_text = page.extract_text() or ""

                page_text = re.sub(
                    r"\s+", " ", page_text
                ).strip()

                if not page_text:
                    continue

                _document_chunks.append({
                    "text": page_text,
                    "program": program,
                    "filename": pdf_path.name,
                    "page": page_number
                })

            print(
                f"Loaded {program} PDF: {pdf_path.name}"
            )

        except Exception as error:

            print(
                f"Could not read {pdf_path.name}: {error}"
            )

    if not _document_chunks:
        raise ValueError(
            "No readable text found in the regulation PDFs."
        )

    document_tokens = [
        tokenize(item["text"])
        for item in _document_chunks
    ]

    document_count = len(document_tokens)
    document_frequency = Counter()

    for tokens in document_tokens:
        document_frequency.update(set(tokens))

    _idf = {
        word: math.log(
            (1 + document_count) / (1 + frequency)
        ) + 1
        for word, frequency in document_frequency.items()
    }

    _document_vectors = []

    for tokens in document_tokens:

        counts = Counter(tokens)
        total = max(len(tokens), 1)

        vector = {
            word: (count / total) * _idf.get(word, 0)
            for word, count in counts.items()
        }

        _document_vectors.append(vector)

    _index_loaded = True

    print("Regulations PDF index created successfully.")
    print("Total PDF pages indexed:", len(_document_chunks))


# --------------------------------------------------
# 4. SIMILARITY CALCULATION
# --------------------------------------------------

def cosine_score(query_vector, document_vector):

    dot_product = sum(
        value * document_vector.get(word, 0)
        for word, value in query_vector.items()
    )

    query_length = math.sqrt(
        sum(value * value for value in query_vector.values())
    )

    document_length = math.sqrt(
        sum(value * value for value in document_vector.values())
    )

    if query_length == 0 or document_length == 0:
        return 0

    return dot_product / (
        query_length * document_length
    )


# --------------------------------------------------
# 5. KEYWORD BOOSTING
# --------------------------------------------------

def keyword_boost(question, document_text):

    q = question.lower()
    text = document_text.lower()

    boost = 0

    attendance_question = any(word in q for word in [
        "attendance", "attendence", "absent",
        "shortage", "exam", "examination",
        "eligible", "eligibility", "appear"
    ])

    if attendance_question:

        important_terms = [
            "attendance",
            "75 percent",
            "75%",
            "65 percent",
            "65%",
            "examination",
            "medical reasons",
            "hospitalization",
            "accident",
            "specific illness",
            "sports events",
            "prior permission",
            "exemption",
            "documents",
            "R7.3",
            "R7.4",
            "R7.5",
            "R7.6",
            "R7.7"
        ]

        for term in important_terms:
            if term in text:
                boost += 0.08

    if "credit" in q or "credits" in q:

        credit_terms = [
            "total credits",
            "lecture",
            "tutorial",
            "practical",
            "laboratory",
            "internship",
            "industrial training",
            "semester"
        ]

        for term in credit_terms:
            if term in text:
                boost += 0.06

    if re.search(r"\br7\.\d+\b", text):
        boost += 0.05

    return boost


# --------------------------------------------------
# 6. RETRIEVE PROGRAMME-SPECIFIC CONTEXT
# --------------------------------------------------

def retrieve_context(question, selected_program=None, top_k=8):

    load_regulations()

    program = normalize_program(selected_program)

    if not program:
        program = detect_program(question)

    if not program:
        return None, "ASK_PROGRAM"

    expanded_question = expand_question(question)

    query_tokens = tokenize(expanded_question)
    query_counts = Counter(query_tokens)

    total = max(len(query_tokens), 1)

    query_vector = {
        word: (count / total) * _idf.get(word, 0)
        for word, count in query_counts.items()
        if word in _idf
    }

    if not query_vector:
        return None, None

    ranked_results = []

    for index, document in enumerate(_document_chunks):

        # STRICT PROGRAMME FILTERING
        if document["program"] != program:
            continue

        score = cosine_score(
            query_vector,
            _document_vectors[index]
        )

        score += keyword_boost(
            question,
            document["text"]
        )

        ranked_results.append((score, document))

    ranked_results.sort(
        key=lambda item: item[0],
        reverse=True
    )

    results = [
        document
        for score, document in ranked_results[:top_k]
        if score > 0
    ]

    if not results:
        return None, None

    context = ""

    for item in results:

        context += (
            f"\n[Document: {item['filename']}, "
            f"Programme: {item['program']}, "
            f"Page: {item['page']}]\n"
            f"{item['text']}\n"
        )

    return context, results


# --------------------------------------------------
# 7. GENERATE STUDENT ANSWER
# --------------------------------------------------

def generate_answer(question, selected_program=None, selected_year=None):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing in .env"
        )

    program = normalize_program(selected_program)

    if not program:
        program = detect_program(question)

    if not program:
        return (
            "Mudhalil unga programme select pannunga: "
            "B.Tech, M.Tech, illa Ph.D."
        )

    if not selected_year:
        selected_year = "Not specified"

    context, sources = retrieve_context(
        question,
        selected_program=program
    )

    if sources == "ASK_PROGRAM":
        return (
            "Programme select pannunga: "
            "B.Tech, M.Tech, illa Ph.D."
        )

    if not context:
        return (
            f"Selected programme: {program}.\n"
            "Indha question-ku relevant information "
            "uploaded programme regulations PDF-la kidaikkala. "
            "Konjam question-ah more details-oda kekkunga."
        )

    client = Groq(api_key=api_key)

    system_prompt = """
You are STUDENTS AI, a PMIST College Regulations Assistant.

You must answer using ONLY the official PDF context supplied.

STUDENT-FRIENDLY LANGUAGE:

1. Use simple spoken Tamil written in English letters (Thanglish).
2. Sound like a helpful senior explaining to a student.
3. Explain difficult English regulation terms simply.
4. Keep important official terms such as HOD, Dean (FET),
   attendance, exemption and end semester examination.
5. Give the direct answer first.
6. Use short paragraphs and numbered points when needed.
7. Avoid tables for ordinary questions.

STRICT PROGRAMME RULES:

1. The selected programme is the authority for the question.
2. Use only the supplied PDF context for that programme.
3. Never mix B.Tech, M.Tech and Ph.D. regulations.
4. Never answer using another programme's rules.
5. The selected year is additional student context.
6. Do not invent year-specific rules.
7. If the supplied PDF does not contain the answer,
   clearly say that the information is not available
   in the selected programme's uploaded regulations.

STRICT ACCURACY:

1. Do not invent rules, percentages, conditions or exceptions.
2. Preserve the exact meaning of official regulations.
3. Do not remove important conditions while simplifying.
4. Do not guarantee permission or eligibility unless
   the PDF explicitly supports it.
5. Explain all relevant conditions and exceptions.
6. Mention actual regulation clause and PDF page number.
7. Do not use outside knowledge or general college practices.

ANSWER STRUCTURE:

1. Direct answer.
2. Simple Thanglish explanation.
3. Important conditions or exceptions.
4. Next step, only if supported by the PDF.
5. Regulation clause and PDF page reference.

Your answer must sound like a helpful senior
explaining official regulations to a student.
"""

    user_prompt = f"""
SELECTED PROGRAMME: {program}

SELECTED STUDENT YEAR: {selected_year}

STUDENT QUESTION:
{question}

OFFICIAL REGULATIONS PDF CONTEXT:
{context}

Answer the student's question using only this context.

Important:
- Answer for the selected programme only.
- Consider the selected year as student context.
- Do not invent year-specific rules.
- Use easy Thanglish.
- Give the direct answer first.
- Mention correct regulation clause and PDF page.
"""

    response = client.chat.completions.create(
        model=os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b"
        ),
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.1
    )

    return response.choices[0].message.content
