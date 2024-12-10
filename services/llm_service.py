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
            {
                "questions": [
                    {
                        "question": "question text",
                        "answer": "answer text",
                        "explanation": "explanation text"
                    }
                ]
            }
            
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
            """Generate {num_questions} {question_type} questions about {topic} in {subject}.
            The questions should be at {difficulty} difficulty level.
            
            Return the response in the following JSON format:
            {{
                "questions": [
                    {{
                        "question": "question text",
                        "answer": "answer text",
                        "options": ["Option A", "Option B", "Option C", "Option D"] // Only for multiple choice questions
                        "explanation": "explanation text"
                    }}
                ]
            }}
            
            Topic context: {context}
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

    def extract_context_from_text(self, text: str, question_type: str, question_quantity: int) -> List[Dict]:
        context_prompt = PromptTemplate.from_template(
            """
        You are an expert teacher. Based on the following text, create {questionQuantity} {questionType} questions.
        Each question should be challenging but appropriate for students studying this material.

        Text: {text}

        Return the response in the following JSON format:
        {{
            "questions": [
                {{
                    "question": "question text",
                    "answer": "answer text",
                    "options": ["Option A", "Option B", "Option C", "Option D"] // Only for multiple choice questions
                    "explanation": "explanation text"
                }}
            ]
        }}

        Ensure that the JSON is valid and can be parsed.
        """
        )

        formatted_prompt = context_prompt.format(
            text=text, questionType=question_type, questionQuantity=question_quantity
        )
        response = self.llm.invoke(formatted_prompt)
        parsed_output = self.output_parser.parse(response.content)

        return parsed_output["questions"]
