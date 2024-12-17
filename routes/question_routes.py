from flask import Blueprint, request, jsonify
from services.llm_service import LLMService
from PyPDF2 import PdfReader
from models.models import QuestionModel, SessionModel, db_session
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

        # Create session and store questions
        session = SessionModel()
        db_session.add(session)
        db_session.commit()

        for question in questions:
            question_model = QuestionModel(
                session_id=session.id,
                question=question["question"],
                type=question["type"],
                explanation=question.get("explanation"),
            )
            
            # Set answer using the new method
            question_model.set_answer(question.get("answer"))
            
            # Handle different question types
            if question["type"].upper() == "MCQ":  # Make case-insensitive comparison
                question_model.set_options(question.get("options", []))
            elif question["type"] == "match_the_following":
                question_model.set_match_pairs(question.get("match_the_following_pairs"))
            elif question["type"] == "sequence":
                question_model.set_sequence_items(question.get("sequence_items"))

            db_session.add(question_model)

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
        questions = db_session.query(QuestionModel).filter_by(session_id=quiz_id).all()
        
        if not questions:
            return jsonify({"success": False, "error": "No questions found"}), 404

        question_list = []
        for question in questions:
            question_data = {
                "question": question.question,
                "type": question.type,
                "answer": question.get_answer(),
                "explanation": question.explanation,
            }

            # Add type-specific data
            if question.type == "MCQ":
                question_data["options"] = question.get_options()
            elif question.type == "match_the_following":
                pairs = question.get_match_pairs()
                if isinstance(pairs, dict):
                    question_data["match_the_following_pairs"] = {
                        "left": pairs.get("left", []),
                        "right": pairs.get("right", [])
                    }
                    # Convert string answer back to dict if needed
                    answer = question.get_answer()
                    if isinstance(answer, str) and answer.startswith('{'):
                        try:
                            answer = json.loads(answer.replace("'", '"'))
                        except:
                            pass
                    question_data["answer"] = answer
            elif question.type == "sequence":
                question_data["sequence_items"] = question.get_sequence_items()

            question_list.append(question_data)

        return jsonify({
            "success": True,
            "questions": question_list
        })
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
                "answer": q.get_answer(),
                "options": q.get_options(),
                "match_the_following_pairs": q.get_match_pairs(),
                "sequence_items": q.get_sequence_items()
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