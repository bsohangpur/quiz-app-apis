from flask import Blueprint, request, jsonify
from services.llm_service import LLMService
from PyPDF2 import PdfReader
from models.models import SessionModel, db_session
from typing import List, Dict
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import json
from PIL import Image
import io
import base64


question_bp = Blueprint("questions", __name__)
llm_service = LLMService(provider="openai")  # or "openai"


def compress_image(image_file, max_size_mb=1):
    # Open the image
    img = Image.open(image_file)
    
    # Convert to RGB if necessary
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Initial quality
    quality = 95
    output = io.BytesIO()
    
    # Compress until size is under max_size_mb
    while True:
        output.seek(0)
        output.truncate()
        img.save(output, format='JPEG', quality=quality)
        if len(output.getvalue()) <= max_size_mb * 1024 * 1024 or quality <= 5:
            break
        quality -= 5
    
    output.seek(0)
    return output


def validate_image_size(file_content, max_size_mb=1):
    """Validate that the image size is within limits"""
    size_bytes = len(file_content)
    max_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
    return size_bytes <= max_bytes


def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            # Read the image and encode it
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        print(f"Error encoding image: {str(e)}")
        return None


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


# @question_bp.route("/upload-context", methods=["POST"])
# def upload_context():
#     if "file" not in request.files:
#         return jsonify({"error": "No file provided"}), 400

#     file = request.files["file"]
    
#     if file.filename.endswith(('.jpg', '.jpeg', '.png')):
#         # Handle image file
#         try:
#             # Read file content
#             file_content = file.read()
            
#             # Check file size
#             if not validate_image_size(file_content):
#                 return jsonify({"error": "Image size must be less than 1MB"}), 400
            
#             # Convert to base64
#             base64_image = base64.b64encode(file_content).decode('utf-8')
            
#             # Create a smaller content string
#             content = f"An image was provided. Please analyze this image and generate questions based on its content."
            
#             # Generate questions using the image content
#             questions = llm_service.generate_questions(
#                 subject="Image Analysis",
#                 topic="Image Content",
#                 question_type=request.form.get("question_type", "mcq"),
#                 difficulty=request.form.get("difficulty", "medium"),
#                 num_questions=int(request.form.get("num_questions", 5)),
#                 context=content
#             )
            
#             # Create session and store questions
#             session = SessionModel()
#             session.set_questions(questions)
#             db_session.add(session)
#             db_session.commit()
            
#             return jsonify({
#                 "success": True,
#                 "questions": questions,
#                 'quiz_id': session.id
#             })
            
#         except Exception as e:
#             return jsonify({"error": f"Error processing image: {str(e)}"}), 400
#     elif file.filename.endswith(".pdf"):
#         pdf_reader = PdfReader(file)
#         text_content = ""
#         for page in pdf_reader.pages:
#             text_content += page.extract_text()

#     try:
#         context = llm_service.extract_context_from_text(text_content)
#         return jsonify({"success": True, "context": context})
#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)}), 500


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
        data = request.get_json()
        user_answers = data.get("answers", [])

        # Get questions from session
        session = db_session.query(SessionModel).filter_by(id=quiz_id).first()
        if not session:
            return jsonify({"success": False, "error": "Quiz not found"}), 404

        # Get questions directly - no need to parse JSON again
        questions = session.get_questions()

        # Evaluate each answer
        evaluation_results = []
        for q, user_answer in zip(questions, user_answers):

            # Ensure user_answer is a dictionary
            if not isinstance(user_answer, dict) or "answer" not in user_answer:
                return jsonify({"success": False, "error": "Invalid user answer format"}), 400

            # Convert image paths to base64 if present
            if isinstance(user_answer.get("answer"), dict) and "image" in user_answer["answer"]:
                image_data = user_answer["answer"]["image"]
                if image_data and "path" in image_data:
                    base64_image = get_base64_image(image_data["path"])
                    if base64_image:
                        user_answer["answer"]["image"] = {
                            "base64": base64_image,
                            "originalPath": image_data["path"]
                        }

            # Decode the base64 image if present and prepare it for LLM evaluation
            if "image" in user_answer["answer"] and "base64" in user_answer["answer"]["image"]:
                base64_image_data = user_answer["answer"]["image"]
                # Attach the base64 image data directly to the user answer
                user_answer["answer"]["image_data"] = base64_image_data

            # Ensure q is a dictionary
            if not isinstance(q, dict) or "question" not in q or "answer" not in q:
                return jsonify({"success": False, "error": "Invalid question format"}), 400

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
            "detailed_results": evaluation_results,
            **score_data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error evaluating answers: {str(e)}"
        }), 500
