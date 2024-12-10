from flask import Blueprint, request, jsonify
from services.llm_service import LLMService
from PyPDF2 import PdfReader

question_bp = Blueprint("questions", __name__)
llm_service = LLMService(provider="gemini")  # or "openai"


@question_bp.route("/generate", methods=["POST"])
def generate_questions():
    try:
        if request.files:
            file = request.files["file"]
            num_questions = request.form.get("num_questions")
            question_type = request.form.get("question_type")

            if file.filename.endswith(".pdf"):
                pdf_reader = PdfReader(file)
                length_of_page_in_pdf = len(pdf_reader.pages)
                text_content = ""

                if length_of_page_in_pdf > 30:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "File must have less than 30 pages",
                            }
                        ),
                        400,
                    )

                for page in pdf_reader.pages:
                    text_content += page.extract_text()

                context = llm_service.extract_context_from_text(
                    text=text_content,
                    question_quantity=int(num_questions),
                    question_type=question_type,
                )

                return jsonify({"success": True, "questions": context})
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid file format file must be pdf",
                        }
                    ),
                    400,
                )

        else:
            data = request.json
            questions = llm_service.generate_questions(
                subject=data["subject"],
                topic=data["topic"],
                question_type=data["question_type"],
                difficulty=data["difficulty"],
                num_questions=data["num_questions"],
            )

            return jsonify({"success": True, "questions": questions})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@question_bp.route("/upload-context", methods=["POST"])
def upload_context():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename.endswith(".pdf"):
        pdf_reader = PdfReader(file)
        text_content = ""
        for page in pdf_reader.pages:
            text_content += page.extract_text()

    try:
        context = llm_service.extract_context_from_text(text_content)
        return jsonify({"success": True, "context": context})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
