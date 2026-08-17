from typing import List, Dict, Any
from app.models.enums import QuestionType
from app.models.exam import Question

class GradingService:
    @staticmethod
    def grade_multiple_choice(question: Question, answer_data: Dict[str, Any]) -> float:
        """
        answer_data: {"selected_option_ids": ["uuid-1", "uuid-2"]} or {"selected_option_id": "uuid-1"}
        """
        selected_ids = set()
        if "selected_option_ids" in answer_data:
            selected_ids = {str(i) for i in answer_data["selected_option_ids"]}
        elif "selected_option_id" in answer_data:
            selected_ids = {str(answer_data["selected_option_id"])}

        correct_options = [opt for opt in question.options if opt.is_correct]
        correct_ids = {str(opt.id) for opt in correct_options}
        
        # Exact match required for full points (or implement partial credit if needed)
        if selected_ids == correct_ids and len(correct_ids) > 0:
            return float(question.points)
        return 0.0

    @staticmethod
    def grade_fill_in_blank(question: Question, answer_data: Dict[str, Any]) -> float:
        """
        question.metadata_json: {"blanks": [{"blank_index": 0, "acceptable_answers": ["apple", "quả táo"]}, ...]}
        answer_data: {"blanks": {"0": "apple", "1": "orange"}}
        """
        expected_blanks = question.metadata_json.get("blanks", [])
        provided_blanks = answer_data.get("blanks", {})
        
        if not expected_blanks:
            return 0.0
            
        points_per_blank = float(question.points) / len(expected_blanks)
        score = 0.0
        
        for expected in expected_blanks:
            blank_idx = str(expected.get("blank_index"))
            acceptable = expected.get("acceptable_answers", [])
            
            provided_val = str(provided_blanks.get(blank_idx, "")).strip().lower()
            
            if not provided_val:
                continue
                
            # Check if the provided value matches ANY of the acceptable answers
            for ans in acceptable:
                if str(ans).strip().lower() == provided_val:
                    score += points_per_blank
                    break # Matched one of the acceptable answers, move to next blank
                    
        return float(score)

    @staticmethod
    def grade_matching(question: Question, answer_data: Dict[str, Any]) -> float:
        """
        question.metadata_json: {"pairs": [{"left": "Cat", "right": "Animal"}, {"left": "Apple", "right": "Fruit"}]}
        answer_data: {"matches": [{"left": "Cat", "right": "Animal"}, {"left": "Apple", "right": "Vegetable"}]}
        """
        expected_pairs = question.metadata_json.get("pairs", [])
        provided_matches = answer_data.get("matches", [])
        
        if not expected_pairs:
            return 0.0
            
        points_per_pair = float(question.points) / len(expected_pairs)
        score = 0.0
        
        for expected in expected_pairs:
            for match in provided_matches:
                if match.get("left") == expected.get("left") and match.get("right") == expected.get("right"):
                    score += points_per_pair
                    break
                    
        return float(score)

    @classmethod
    def grade_question(cls, question: Question, answer_data: Dict[str, Any]) -> float:
        if not answer_data:
            return 0.0
            
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            return cls.grade_multiple_choice(question, answer_data)
        elif question.question_type == QuestionType.FILL_IN_BLANK:
            return cls.grade_fill_in_blank(question, answer_data)
        elif question.question_type == QuestionType.MATCHING:
            return cls.grade_matching(question, answer_data)
            
        return 0.0
