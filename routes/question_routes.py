from flask import Blueprint, request, jsonify
from services.llm_service import LLMService
from PyPDF2 import PdfReader
from models.models import SessionModel, db_session
from typing import List, Dict
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import json

question_bp = Blueprint("questions", __name__)
llm_service = LLMService(provider="openai")  # or "openai"


@question_bp.route("/generate", methods=["POST"])
def generate_questions():
    try:
        if request.files:
            file = request.files["file"]
            num_questions = int(request.form.get("num_questions", 5))
            question_type = request.form.get("question_type", "mcq")
            difficulty = request.form.get("difficulty", "medium")

            if not file.filename.endswith(".pdf"):
                return jsonify({
                    "success": False,
                    "error": "Invalid file format. File must be PDF."
                }), 400

            # Save PDF temporarily
            temp_path = "temp.pdf"
            file.save(temp_path)

            try:
                # Use Langchain's PDF loader
                loader = PyPDFLoader(temp_path)
                pages = loader.load()

                # Check page limit
                if len(pages) > 30:
                    return jsonify({
                        "success": False,
                        "error": "File must have less than 30 pages"
                    }), 400

                # Split text into chunks
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=2000,
                    chunk_overlap=200,
                    length_function=len
                )
                texts = text_splitter.split_documents(pages)
                
                # Combine relevant chunks
                combined_text = " ".join([doc.page_content for doc in texts])

                # Generate questions using the same prompt as generate_questions
                questions = llm_service.generate_questions(
                    subject="Document Analysis",
                    topic="PDF Content",
                    question_type=question_type,
                    difficulty=difficulty,
                    num_questions=num_questions,
                    context=combined_text
                )

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        else:
            data = request.json
            questions = llm_service.generate_questions(
                subject=data["subject"],
                topic=data["topic"],
                question_type=data["question_type"],
                difficulty=data["difficulty"],
                num_questions=data["num_questions"]
            )

        # Create session and store questions as JSON
        session = SessionModel()
        session.set_questions(questions)
        db_session.add(session)
        db_session.commit()

        return jsonify({
            "success": True,
            "questions": questions,
            'quiz_id': session.id
        })

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

@question_bp.route("/quiz/<string:quiz_id>", methods=["GET"])
def get_questions(quiz_id):
    try:
        session = db_session.query(SessionModel).filter_by(id=quiz_id).first()
        
        if not session:
            return jsonify({"success": False, "error": "Quiz not found"}), 404

        questions = session.get_questions()
        return jsonify({
            "success": True,
            "questions": questions
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@question_bp.route("/evaluate/<string:quiz_id>", methods=["POST"])
def evaluate_answers(quiz_id):
    try:
        user_answers = request.json.get("answers", [])
        if not user_answers:
            return jsonify({"success": False, "error": "No answers provided"}), 400

        # Get questions from session
        session = db_session.query(SessionModel).filter_by(id=quiz_id).first()
        if not session:
            return jsonify({"success": False, "error": "Quiz not found"}), 404

        questions = session.get_questions()

        # Evaluate each answer
        evaluation_results = []
        for q, user_answer in zip(questions, user_answers):
            result = llm_service.evaluate_answer(q, user_answer["answer"])
            evaluation_results.append({
                "question": q["question"],
                "user_answer": user_answer["answer"],
                "correct_answer": q["answer"],
                "is_correct": result["is_correct"],
                "explanation": result["explanation"]
            })

        # Calculate overall score
        score_data = llm_service.calculate_quiz_score(evaluation_results)

        return jsonify({
            "success": True,
            "quiz_id": quiz_id,
            **score_data,
            "detailed_results": evaluation_results
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500