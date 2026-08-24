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
    def grade_single_choice(question: Question, answer_data: Dict[str, Any]) -> float:
        """
        answer_data: {"selected_option_id": "uuid-1"} or {"selected_option_ids": ["uuid-1"]}

        Deliberately stricter than `grade_multiple_choice` rather than an
        alias for it. A single-choice question asks for exactly one answer,
        so selecting two options is a malformed answer, not a half-right
        one -- set-comparing it would silently award full marks to a
        submission that picked the correct option *and* a wrong one, as long
        as the question happened to have two correct options recorded.

        A question that does not have exactly one correct option is itself
        malformed. This scores 0 rather than guessing which option was
        intended: awarding points off a broken question would put a wrong
        grade on a retained educational record.
        """
        correct_ids = [str(opt.id) for opt in question.options if opt.is_correct]
        if len(correct_ids) != 1:
            return 0.0

        if "selected_option_id" in answer_data:
            selected = answer_data["selected_option_id"]
            if selected is None:
                return 0.0
            selected_ids = [str(selected)]
        elif "selected_option_ids" in answer_data:
            raw = answer_data["selected_option_ids"] or []
            if not isinstance(raw, (list, tuple, set)):
                return 0.0
            selected_ids = [str(item) for item in raw]
        else:
            return 0.0

        # Exactly one selection, and it is the correct one.
        if len(selected_ids) != 1:
            return 0.0
        if selected_ids[0] != correct_ids[0]:
            return 0.0
        return float(question.points)

    @staticmethod
    def grade_fill_in_blank(question: Question, answer_data: Dict[str, Any]) -> float:
        """
        question.metadata_json: {"blanks": [{"blank_index": 0, "acceptable_answers": ["apple", "quả táo"]}, ...]}
        answer_data: {"blanks": {"0": "apple", "1": "orange"}}
        """
        metadata: dict[str, Any] = (
            question.metadata_json if isinstance(question.metadata_json, dict) else {}
        )
        expected_blanks = metadata.get("blanks", [])
        provided_blanks = answer_data.get("blanks", {})
        
        if (
            not isinstance(expected_blanks, list)
            or not expected_blanks
            or not isinstance(provided_blanks, dict)
        ):
            return 0.0
            
        points_per_blank = float(question.points) / len(expected_blanks)
        score = 0.0
        
        for expected in expected_blanks:
            if not isinstance(expected, dict):
                return 0.0
            blank_idx = str(expected.get("blank_index"))
            acceptable = expected.get("acceptable_answers", [])
            if not isinstance(acceptable, list):
                return 0.0
            
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
        metadata: dict[str, Any] = (
            question.metadata_json if isinstance(question.metadata_json, dict) else {}
        )
        raw_expected_pairs = metadata.get("pairs", [])
        provided_matches = answer_data.get("matches", [])
        
        if not isinstance(raw_expected_pairs, list) or not raw_expected_pairs:
            return 0.0

        expected_pairs: list[tuple[str, str]] = []
        expected_lefts: set[str] = set()
        expected_rights: set[str] = set()
        for pair in raw_expected_pairs:
            if not isinstance(pair, dict):
                return 0.0
            left = pair.get("left")
            right = pair.get("right")
            if not isinstance(left, str) or not isinstance(right, str):
                return 0.0
            if left in expected_lefts or right in expected_rights:
                return 0.0
            expected_lefts.add(left)
            expected_rights.add(right)
            expected_pairs.append((left, right))

        if not isinstance(provided_matches, list):
            return 0.0
        if len(provided_matches) > len(expected_pairs):
            return 0.0

        provided_pairs: list[tuple[str, str]] = []
        provided_lefts: set[str] = set()
        provided_rights: set[str] = set()
        for match in provided_matches:
            if not isinstance(match, dict):
                return 0.0
            left = match.get("left")
            right = match.get("right")
            if not isinstance(left, str) or not isinstance(right, str):
                return 0.0
            if left not in expected_lefts or right not in expected_rights:
                return 0.0
            if left in provided_lefts or right in provided_rights:
                return 0.0
            provided_lefts.add(left)
            provided_rights.add(right)
            provided_pairs.append((left, right))

        points_per_pair = float(question.points) / len(expected_pairs)
        expected_pair_set = set(expected_pairs)
        correct_count = sum(pair in expected_pair_set for pair in provided_pairs)
        return float(correct_count * points_per_pair)

    @classmethod
    def grade_question(cls, question: Question, answer_data: Dict[str, Any]) -> float:
        if not answer_data:
            return 0.0
            
        if question.question_type == QuestionType.SINGLE_CHOICE:
            return cls.grade_single_choice(question, answer_data)
        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            return cls.grade_multiple_choice(question, answer_data)
        elif question.question_type == QuestionType.FILL_IN_BLANK:
            return cls.grade_fill_in_blank(question, answer_data)
        elif question.question_type == QuestionType.MATCHING:
            return cls.grade_matching(question, answer_data)
            
        return 0.0
