from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Dict
import os


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
        question_prompt = PromptTemplate.from_template(
            """
                Generate {num_questions} {question_type} questions about {topic} in {subject}.  
                The questions should be at {difficulty} difficulty level.  

                For "match_the_following" questions, provide key-value pairs as follows:  
                - **Keys**: Items to match on the left.  
                - **Values**: Items to match on the right.
                
                For "sequence" questions, provide a series of items that the student needs to arrange in the correct order.  

                **Input**:  
                Topic context: {context}  

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
                            "type": "which type of quiz generated (mcq, fill_in_blank, true_false, short, long, code, sequence, diagram, match_the_following)",
                            "match_the_following_pairs": {{ // Only for match_the_following questions
                                "Key 1": "Value 1",
                                "Key 2": "Value 2",
                                "Key 3": "Value 3"
                            }},
                            "correctAnswer": [ // Only for sequence type questions
                                {{ "id": "1", "content": "Correct Answer 1" }},
                                {{ "id": "2", "content": "Correct Answer 2" }},
                                {{ "id": "3", "content": "Correct Answer 3" }},
                            ]
                        }}
                    ]
                }}
            """
        )
        formatted_prompt = question_prompt.format(
            subject=subject,
            topic=topic,
            question_type=question_type,
            difficulty=difficulty,
            num_questions=num_questions,
            context=context,
        )

        response = self.llm.invoke(formatted_prompt)
        parsed_output = self.output_parser.parse(response.content)

        return parsed_output["questions"]

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
                            "type": "which type of quiz generated (mcq, fill_in_blank, true_false, short, long, code, sequence, diagram, match_the_following)",
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

    def evaluate_answer(self, question_data: dict, user_answer: str) -> dict:
        """
        Evaluate a user's answer using LLM
        """
        evaluation_prompt = PromptTemplate.from_template(
            """
            Evaluate if the user's answer is correct for the given question.
            
            Question: {question}
            Correct Answer: {correct_answer}
            User Answer: {user_answer}
            Question Type: {question_type}

            Consider the following criteria:
            1. For MCQ and true/false questions, check for exact match
            2. For short/long answers, check for semantic correctness
            3. For match_the_following, check if pairs match correctly
            4. For fill_in_blank, check if the answer is semantically correct

            Return the evaluation in this JSON format:
            {
                "is_correct": true/false,
                "explanation": "Brief explanation of why the answer is correct/incorrect",
                "score": "numerical_score_between_0_and_1"
            }
            """
        )

        try:
            formatted_prompt = evaluation_prompt.format(
                question=question_data["question"],
                correct_answer=question_data["answer"],
                user_answer=user_answer,
                question_type=question_data["type"]
            )

            response = self.llm.invoke(formatted_prompt)
            evaluation = self.output_parser.parse(response.content)
            return evaluation

        except Exception as e:
            # Fallback to basic string matching
            is_match = self._basic_string_match(
                user_answer, 
                question_data["answer"],
                question_data["type"]
            )
            return {
                "is_correct": is_match,
                "explanation": "Basic string matching used due to evaluation error",
                "score": 1.0 if is_match else 0.0
            }

    def _basic_string_match(self, user_answer: str, correct_answer: str, question_type: str) -> bool:
        """
        Fallback method for basic answer matching when LLM fails
        """
        user_answer = str(user_answer).lower().strip()
        correct_answer = str(correct_answer).lower().strip()

        if question_type in ["mcq", "true_false", "fill_in_blank"]:
            return user_answer == correct_answer
        
        elif question_type == "match_the_following":
            try:
                user_pairs = eval(user_answer) if isinstance(user_answer, str) else user_answer
                correct_pairs = eval(correct_answer) if isinstance(correct_answer, str) else correct_answer
                return user_pairs == correct_pairs
            except:
                return False
        
        else:  # For short and long answers
            # Simple word overlap check
            user_words = set(user_answer.split())
            correct_words = set(correct_answer.split())
            overlap = len(user_words.intersection(correct_words))
            total_words = len(correct_words)
            return overlap / total_words >= 0.7  # 70% word match threshold

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
            "rank": self._determine_rank(score_percentage)
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
