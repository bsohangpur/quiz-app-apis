from flask import Blueprint, request, jsonify
from services.llm_service import LLMService
from PyPDF2 import PdfReader
from models.models import QuestionModel, SessionModel, db_session
from typing import List, Dict

question_bp = Blueprint("questions", __name__)
llm_service = LLMService(provider="openai")  # or "openai"


@question_bp.route("/generate", methods=["POST"])
def generate_questions():
    try:
        if request.files:
            file = request.files["file"]
            num_questions = request.form.get("num_questions")
            question_type = request.form.get("question_type")
            quizs = []

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

                quizs = context
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

            # return jsonify({"success": True, "questions": questions})

        
        quizs = questions
        session = SessionModel()  
        db_session.add(session)
        db_session.commit()

        for question in questions:
            question_data = {
                "session_id": session.id,
                "question": question["question"],
                "type": question["type"],
                "answer": question.get("answer", " "),
                "explanation": question.get("explanation"),
                "options": question.get("options"),
                "match_the_following_pairs": question.get("match_the_following_pairs"),
                "correct_answer": question.get("correct_answer"),
            }
            quiz = QuestionModel(**question_data)
            db_session.add(quiz)

        db_session.commit() 

        return jsonify({"success": True, "questions": quizs, 'quiz_id':session.id})
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
        quizs = []
        questions = db_session.query(QuestionModel).filter_by(session_id=quiz_id).all()

        if not questions:
            return jsonify({"success": False, "error": "No questions found"}), 404

        for question in questions:
            question_data = {
                "question": question.question,
                "type": question.type,
                "answer": question.answer,
                "explanation": question.explanation,
                "options": question.options,
                "match_the_following_pairs": question.match_the_following_pairs,
                "correct_answer": question.correct_answer,
            }
            quizs.append(question_data)
            

        return jsonify({"success": True, "questions": quizs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@question_bp.route("/evaluate/<string:quiz_id>", methods=["POST"])
def evaluate_answers(quiz_id):
    try:
        user_answers = request.json.get("answers", [])
        if not user_answers:
            return jsonify({"success": False, "error": "No answers provided"}), 400

        # Get original questions from database
        questions = db_session.query(QuestionModel).filter_by(session_id=quiz_id).all()
        if not questions:
            return jsonify({"success": False, "error": "Quiz not found"}), 404

        # Evaluate each answer using LLM service
        evaluation_results = []
        for q, user_answer in zip(questions, user_answers):
            question_data = {
                "question": q.question,
                "type": q.type,
                "answer": q.answer,
                "options": q.options,
                "match_the_following_pairs": q.match_the_following_pairs
            }
            
            result = llm_service.evaluate_answer(question_data, user_answer["answer"])
            evaluation_results.append({
                "question": q.question,
                "user_answer": user_answer["answer"],
                "correct_answer": q.answer,
                "is_correct": result["is_correct"],
                "explanation": result["explanation"]
            })

        # Calculate overall score and rank
        score_data = llm_service.calculate_quiz_score(evaluation_results)

        response = {
            "success": True,
            "quiz_id": quiz_id,
            **score_data,
            "detailed_results": evaluation_results
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500