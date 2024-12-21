from typing import List, Optional, Union, Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import json
import ast
import random
import base64
import io
from PIL import Image

def subjectTopicTemplate(subject, topic, questionType, questionQuantity):
    return f"""
        You are an expert teacher in {subject}, specifically in the topic of {topic}.
        Create {questionQuantity} {questionType} questions about {topic} in {subject}.
        Each question should be challenging but appropriate for students studying this topic.

        Format your response as a JSON array of objects, where each object has the following structure:
        {{
        "question": "The question text",
        "type": "{questionType}",
        "options": ["Option A", "Option B", "Option C", "Option D"] // Only for multiple choice questions
        "answer": "The correct answer or explanation"
        }}

        Ensure that the JSON is valid and can be parsed.
        """


def textTemplate(questionType, questionQuantity, text):
    return f"""
        You are an expert teacher. Based on the following text, create {questionQuantity} {questionType} questions.
        Each question should be challenging but appropriate for students studying this material.

        Text: {text}

        Format your response as a JSON array of objects, where each object has the following structure:
        {{
        "question": "The question text",
        "type": "{questionType}",
        "options": ["Option A", "Option B", "Option C", "Option D"] // Only for multiple choice questions
        "answer": "The correct answer or explanation"
        }}

        Ensure that the JSON is valid and can be parsed.
        """


class LLMService:
    def __init__(self, provider: str = "gemini"):
        self.provider = provider
        if provider == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                temperature=0.7,
            )
        else:
            self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

        self.question_prompt = PromptTemplate.from_template(
            """Generate {num_questions} {question_type} questions about {topic} in {subject}.
            The questions should be at {difficulty} difficulty level.
            
            Return the response in the following JSON format:
            {{
                "questions": [
                    {{
                        "question": "question text",
                        "answer": "answer text",
                        "explanation": "explanation text"
                    }}
                ]
            }}
            
            Topic context: {context}
            """
        )

        self.output_parser = JsonOutputParser()

    def generate_questions(
        self,
        subject: str,
        topic: str,
        question_type: str,
        difficulty: str,
        num_questions: int,
        context: str = "",
    ) -> List[Dict]:
        all_questions = []
        question_types = question_type
        num_questions_per_type = num_questions // len(question_types)
        remainder = num_questions % len(question_types)

        for i, q_type in enumerate(question_types):
            n_questions = num_questions_per_type + (1 if i < remainder else 0)
            if n_questions > 0:
                question_prompt = PromptTemplate.from_template(
                    """
                    Generate {num_questions} {question_type} questions about {topic} in {subject}.
                    The questions should be at {difficulty} difficulty level.

                    Follow these format rules based on question_type:
                    - For Long Answer questions:
                        - Question type must be "Long Answer"
                        - Should require a detailed explanation.
                        Example:
                        {{
                            "question": "Explain the concept of...",
                            "type": "Long Answer",
                            "answer": "Detailed explanation here"
                        }}

                    - For Diagram questions:
                        - Question type must be "Diagram"
                        - Should require a visual representation or diagram.
                        Example:
                        {{
                            "question": "Draw a diagram illustrating...",
                            "type": "Diagram",
                            "answer": "Description of the diagram"
                        }}

                    - For MCQ questions:
                        - Question type must be "MCQ" (uppercase)
                        - Must include "options" array with exactly 4 choices
                        - Options must be properly formatted
                        Example:
                        {{
                            "question": "What is X?",
                            "type": "MCQ",
                            "options": [
                                "Option A",
                                "Option B",
                                "Option C",
                                "Option D"
                            ],
                            "answer": "Option A",
                            "explanation": "Explanation here"
                        }}

                    - For match_the_following questions:
                        - Question type must be "match_the_following"
                        - Must include match_the_following_pairs with left/right arrays
                        Example:
                        {{
                            "question": "Match the following...",
                            "type": "match_the_following",
                            "match_the_following_pairs": {{
                                "left": ["A", "B", "C"],
                                "right": ["1", "2", "3"]
                            }},
                            "answer": {{"A": "1", "B": "2", "C": "3"}},
                            "explanation": "Explanation here"
                        }}

                    Context to use for questions: {context}

                    Return the response in the following JSON format:
                    {{
                        "questions": [
                            {{
                                "question": "question text",
                                "type": "{question_type}",
                                "answer": "answer text",
                                "explanation": "explanation text",
                                "options": ["A", "B", "C", "D"],  // For MCQ only
                                "match_the_following_pairs": {{...}},  // For match_the_following only
                                "sequence_items": [...] // For sequence only
                            }}
                        ]
                    }}

                    Ensure that:
                    1. Question type is strictly one of the specified types ("Long Answer", "Diagram", "MCQ", "match_the_following").
                    2. MCQ questions MUST have options array.
                    3. All JSON is properly formatted.
                    """
                )

                formatted_prompt = question_prompt.format(
                    subject=subject,
                    topic=topic,
                    question_type=q_type,
                    difficulty=difficulty,
                    num_questions=n_questions,
                    context=context,
                )

                response = self.llm.invoke(formatted_prompt)
                parsed_output = self.output_parser.parse(response.content)

                if "questions" in parsed_output:
                    for question in parsed_output["questions"]:
                        question["type"] = q_type  # Ensure the type is correctly set
                        if question["type"] == "match_the_following":
                            pairs = question["match_the_following_pairs"]
                            right_options = pairs["right"]
                            shuffled_right = right_options.copy()
                            random.shuffle(shuffled_right)
                            pairs["right"] = shuffled_right

                            correct_mapping = {}
                            for left, right in zip(pairs["left"], right_options):
                                correct_mapping[left] = right
                            question["answer"] = correct_mapping
                    all_questions.extend(parsed_output["questions"])

        return all_questions

    def extract_context_from_text(
        self, text: str, question_type: str, question_quantity: int
    ) -> List[Dict]:
        context_prompt = PromptTemplate.from_template(
            """
                You are an expert teacher. Based on the following text, create {questionQuantity} {questionType} questions.  
                Each question should be challenging but appropriate for students studying this material.  

                For "match_the_following" questions, provide a key-value pair format as follows:  
                - **Keys**: Items to match on the left.  
                - **Values**: Items to match on the right.  

                **Input**:  
                Text: {text}  

                **Output**:  
                Return the response in the following JSON format:  
                ```json
                {{
                    "questions": [
                        {{
                            "question": "question text",
                            "answer": "answer text",
                            "options": ["Option A", "Option B", "Option C", "Option D"], // Only for multiple choice questions
                            "explanation": "explanation text",
                            "type":"which type of quiz generated from this only mcq, fill_in_blank, true_false, short, long, code, sequence, diagram, match_the_following"
                            "match_the_following_pairs": {{ // Only for match_the_following questions
                                "Key 1": "Value 1",
                                "Key 2": "Value 2",
                                "Key 3": "Value 3"
                            }},
                            "correctAnswer": [ // Only for sequence questions
                                {{ "id": "1", "content": "Correct Answer 1" }},
                                {{ "id": "2", "content": "Correct Answer 2" }},
                                {{ "id": "3", "content": "Correct Answer 3" }},
                            ]
                        }}
                    ]
                }}
        """
        )

        formatted_prompt = context_prompt.format(
            text=text, questionType=question_type, questionQuantity=question_quantity
        )
        response = self.llm.invoke(formatted_prompt)
        parsed_output = self.output_parser.parse(response.content)

        return parsed_output["questions"]

    def evaluate_answer(self, question_data: dict, user_answer: dict) -> dict:
        """
        Evaluate a user's answer using LLM
        """

        base64_str = ""
        mime_type = ""

        if 'image' in user_answer:
            base64_str = user_answer['image']
            mime_type = self._get_media_type(base64_str)
            if mime_type not in ['image/png', 'image/jpeg', 'image/gif', 'image/webp']:
                return {
                    "is_correct": False,
                    "explanation": "Unsupported image format. Supported formats are: png, jpeg, gif, webp.",
                    "score": 0.0,
                }

        processed_user_answer = self._preprocess_answer(
            user_answer, question_data["type"]
        )
        processed_correct_answer = self._preprocess_answer(
            question_data["answer"], question_data["type"]
        )

        # For non-LLM evaluation types, use direct comparison
        if question_data["type"] in [
            "mcq",
            "true_false",
            "sequence",
            "match_the_following",
        ]:
            is_correct = self._basic_string_match(
                processed_user_answer, processed_correct_answer, question_data["type"]
            )
            return {
                "is_correct": is_correct,
                "explanation": self._get_explanation(
                    is_correct, question_data["type"], processed_correct_answer
                ),
                "score": 1.0 if is_correct else 0.0,
            }

        messages = []

        if base64_str:
                messages.append(
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": "Here is the user's submitted image:",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": base64_str
                                }
                            },
                        ]
                    )
                )

        # evaluation_prompt = PromptTemplate.from_template(
        #     """
        #     Evaluate if the user's answer is correct for the given question.

        #     Question: {question}
        #     Correct Answer (Text/Image): {correct_answer}
        #     User Answer (Text/Image): {user_answer}
        #     Question Type: {question_type}

        #     Consider the following criteria based on question type:
        #     - For short answers: Check key concepts and factual accuracy.
        #     - For long answers (text or text + image): Evaluate comprehension, completeness, and relevance. If an image is provided, assess its correctness and alignment with the question.
        #     - For fill_in_blank: Check semantic correctness (text matching expected answer).
        #     - For code questions: Check logic, syntax, and functional correctness.
        #     - For diagram questions (image-only): Compare the user’s image to the correct answer for structure, proportions, and accuracy of labels or annotations.
        #     - For long quiz with images: Evaluate both the textual accuracy and the correctness of the provided image.

        #     Return the evaluation in this JSON format:
        #     {{
        #         "is_correct": true/false,
        #         "explanation": "Brief explanation of why the answer is correct/incorrect, addressing both text and image as needed.",
        #         "score": numerical_score_between_0_and_1
        #     }}
        #     """
        # )

        evaluation_text = f"""
        Evaluate if the user's answer is correct for the given question.
        
        Question: {question_data["question"]}
        Question Type: {question_data["type"]}
        
        Correct Answer Text: {processed_correct_answer}
        User Answer Text: {processed_user_answer}
        
        Consider the following criteria based on question type:
        - For short answers: Check key concepts and factual accuracy.
        - For long answers (text or text + image): Evaluate comprehension, completeness, and relevance.
        - For fill_in_blank: Check semantic correctness.
        - For code questions: Check logic, syntax, and functional correctness.
        - For diagram questions: Compare the user's image to the correct answer for structure, proportions, and accuracy.
        - For long quiz with images: Evaluate both the textual accuracy and image correctness.
        
        Return your evaluation in this JSON format:
        {{
            "is_correct": true/false,
            "explanation": "Brief explanation of why the answer is correct/incorrect, addressing both text and image as needed.",
            "score": numerical_score_between_0_and_1
        }}
        """

        messages.append(HumanMessage(content=evaluation_text))

        # try:
        #     formatted_prompt = evaluation_prompt.format(
        #         question=question_data["question"],
        #         correct_answer=processed_correct_answer,
        #         user_answer=processed_user_answer,
        #         question_type=question_data["type"],
        #     )

        #     response = self.llm.invoke(formatted_prompt)
        #     return self.output_parser.parse(response.content)

        # except Exception as e:
        #     return {
        #         "is_correct": False,
        #         "explanation": f"Error evaluating answer: {str(e)}",
        #         "score": 0.0,
        #     }

        try:
            response = self.llm.invoke(messages)
            return self.output_parser.parse(response.content)
        except Exception as e:
            return {
                "is_correct": False,
                "explanation": f"Error evaluating answer: {str(e)}",
                "score": 0.0,
            }

    def _get_explanation(
        self, is_correct: bool, question_type: str, correct_answer: any
    ) -> str:
        """
        Generate appropriate explanation based on question type
        """
        if is_correct:
            return "Correct answer!"

        try:
            if question_type == "match_the_following":
                if isinstance(correct_answer, str):
                    try:
                        correct_answer = json.loads(correct_answer.replace("'", '"'))
                    except:
                        try:
                            correct_answer = ast.literal_eval(correct_answer)
                        except:
                            return "Incorrect answer."

            type_explanations = {
                "mcq": f"Incorrect. The correct answer is: {correct_answer}",
                "true_false": f"Incorrect. The correct answer is: {correct_answer}",
                "sequence": "Incorrect sequence. The items should be in the following order: "
                + ", ".join(
                    [
                        item["content"] if isinstance(item, dict) else str(item)
                        for item in correct_answer
                    ]
                ),
                "match_the_following": (
                    "Incorrect matches. The correct pairs are: "
                    + ", ".join([f"{k}: {v}" for k, v in correct_answer.items()])
                    if isinstance(correct_answer, dict)
                    else str(correct_answer)
                ),
                "fill_in_blank": f"Incorrect. The correct answer is: {correct_answer}",
                "short": "Incorrect. Your answer doesn't match the expected response.",
                "long": "Incorrect. Your answer doesn't cover the key points.",
                "code": "Incorrect. Your code doesn't match the expected solution.",
            }

            return type_explanations.get(question_type, "Incorrect answer")
        except Exception as e:
            print(f"Error generating explanation: {str(e)}")
            return "Incorrect answer."

    def _preprocess_answer(self, answer: any, question_type: str) -> any:
        """
        Preprocess answers based on question type to ensure consistent format
        """
        if answer is None:
            return answer

        if question_type == "sequence":
            try:
                if isinstance(answer, list):
                    return answer
                if isinstance(answer, str):
                    # Try parsing as JSON first
                    try:
                        parsed = json.loads(answer.replace("'", '"'))
                        # If it's a list of dicts with content, return as is
                        if isinstance(parsed, list) and all(
                            "content" in item for item in parsed
                        ):
                            return parsed
                        # If it's a simple list, convert to content format
                        return [
                            {"content": item, "id": str(i + 1)}
                            for i, item in enumerate(parsed)
                        ]
                    except:
                        # Try ast.literal_eval as fallback
                        try:
                            parsed = ast.literal_eval(answer)
                            if isinstance(parsed, list):
                                return [
                                    {"content": item, "id": str(i + 1)}
                                    for i, item in enumerate(parsed)
                                ]
                            return parsed
                        except:
                            return answer
                return answer
            except:
                return answer

        elif question_type == "match_the_following":
            try:
                # If it's already a dict, return it
                if isinstance(answer, dict):
                    return answer

                # If it's a string representation
                if isinstance(answer, str):
                    # Try parsing as JSON first
                    try:
                        # Remove any single quotes and convert to double quotes
                        cleaned_str = answer.replace("'", '"')
                        # If the string starts with '{', assume it's a dict
                        if cleaned_str.strip().startswith("{"):
                            return json.loads(cleaned_str)
                        return answer
                    except:
                        # Try ast.literal_eval as fallback
                        try:
                            parsed = ast.literal_eval(answer)
                            if isinstance(parsed, dict):
                                return parsed
                            return answer
                        except:
                            return answer
                return answer
            except:
                return answer

        elif question_type in ["mcq", "true_false"]:
            # Normalize MCQ and true/false answers
            if isinstance(answer, str):
                return answer.strip().lower()
            return answer

        elif "image" in answer:
            del answer["image"]
            del answer['image_data']
            return answer

        return answer

    def _basic_string_match(
        self, user_answer: any, correct_answer: any, question_type: str
    ) -> bool:
        """
        Compare answers based on question type
        """
        try:
            if question_type == "sequence":
                if not isinstance(user_answer, list) or not isinstance(
                    correct_answer, list
                ):
                    return False

                # Extract content from both answers
                user_sequence = [
                    item["content"] if isinstance(item, dict) else str(item)
                    for item in user_answer
                ]
                correct_sequence = [
                    item["content"] if isinstance(item, dict) else str(item)
                    for item in correct_answer
                ]

                return user_sequence == correct_sequence

            elif question_type == "match_the_following":
                # Convert string to dict if needed
                if isinstance(user_answer, str):
                    try:
                        user_answer = json.loads(user_answer.replace("'", '"'))
                    except:
                        try:
                            user_answer = ast.literal_eval(user_answer)
                        except:
                            return False

                if isinstance(correct_answer, str):
                    try:
                        correct_answer = json.loads(correct_answer.replace("'", '"'))
                    except:
                        try:
                            correct_answer = ast.literal_eval(correct_answer)
                        except:
                            return False

                if not isinstance(user_answer, dict) or not isinstance(
                    correct_answer, dict
                ):
                    return False

                # Normalize both dictionaries
                user_dict = {
                    str(k).strip().lower(): str(v).strip().lower()
                    for k, v in user_answer.items()
                }
                correct_dict = {
                    str(k).strip().lower(): str(v).strip().lower()
                    for k, v in correct_answer.items()
                }

                return user_dict == correct_dict

            elif question_type in ["mcq", "true_false"]:
                return (
                    str(user_answer).strip().lower()
                    == str(correct_answer).strip().lower()
                )

            else:
                # For other types, use simple string comparison
                return (
                    str(user_answer).strip().lower()
                    == str(correct_answer).strip().lower()
                )

        except Exception as e:
            print(f"Error in _basic_string_match: {str(e)}")
            return False

    def calculate_quiz_score(self, evaluations: List[dict]) -> dict:
        """
        Calculate overall quiz score and rank
        """
        total_questions = len(evaluations)
        correct_answers = sum(1 for eval in evaluations if eval["is_correct"])
        score_percentage = (correct_answers / total_questions) * 100

        return {
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "score_percentage": round(score_percentage, 2),
            "rank": self._determine_rank(score_percentage),
        }

    def _determine_rank(self, percentage: float) -> str:
        """
        Determine rank based on percentage score
        """
        if percentage >= 90:
            return "A+ (Outstanding)"
        elif percentage >= 80:
            return "A (Excellent)"
        elif percentage >= 70:
            return "B (Very Good)"
        elif percentage >= 60:
            return "C (Good)"
        elif percentage >= 50:
            return "D (Fair)"
        else:
            return "F (Needs Improvement)"

    def _get_media_type(self, base64_string):
        if base64_string.startswith("data:"):
            # Extract the media type
            media_type = base64_string.split(";")[0].split(":")[1]
            return media_type
        else:
            return None

# for file
# You are an expert teacher. Based on the following text, create {questionQuantity} {questionType} questions.
# Each question should be challenging but appropriate for students studying this material.

# Text: {text}

# Return the response in the following JSON format:
# {{
#     "questions": [
#         {{
#             "question": "question text",
#             "answer": "answer text",
#             "options": ["Option A", "Option B", "Option C", "Option D"] // Only for multiple choice questions
#             "explanation": "explanation text",
#             "type":"which type of quiz generated from this only mcq, fill_in_blank, true_false, short, long, code, sequence, diagram, match_the_following"
#         }}
#     ]
# }}

# Ensure that the JSON is valid and can be parsed.

# for data in data_list:

# Generate {num_questions} {question_type} questions about {topic} in {subject}.
# The questions should be at {difficulty} difficulty level.

# Return the response in the following JSON format:
# {{
#     "questions": [
#         {{
#             "question": "question text",
#             "answer": "answer text",
#             "options": ["Option A", "Option B", "Option C", "Option D"] // Only for multiple choice questions
#             "explanation": "explanation text",
#             "type":"which type of quiz generated from this only mcq, fill_in_blank, true_false, short, long, code, sequence, diagram, match_the_following"
#         }}
#     ]
# }}

# Topic context: {context}
