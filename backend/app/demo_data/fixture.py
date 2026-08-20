from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import DifficultyLevel, QuestionType


DATASET_ID = "demo-standard-v1"
DEFAULT_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2] / "fixtures" / "demo_standard_v1"
)
GRADEABLE_QUESTION_TYPES = {
    QuestionType.MULTIPLE_CHOICE,
    QuestionType.MATCHING,
    QuestionType.FILL_IN_BLANK,
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExpectedCounts(StrictModel):
    users: int
    topics: int
    materials: int
    document_chunks: int
    topic_briefs: int
    questions: int
    options: int
    flashcard_decks: int
    flashcards: int
    exams: int
    submissions: int
    submission_answers: int
    flashcard_progress: int


class ManifestFiles(StrictModel):
    topics: str
    materials: str
    briefs: str
    questions: str
    exams: str
    flashcards: str
    students: str
    submissions: str


class DemoManifest(StrictModel):
    dataset_id: Literal["demo-standard-v1"]
    version: Literal[1]
    # DATA-DEMO-002: was `alembic_head`, an exact pin that went stale every
    # time an unrelated migration landed (it was still `f9f952e6df1a` after
    # three later heads shipped). A fixture with no schema dependency on
    # anything past this revision should not block on migrations it never
    # needed; the loader instead requires the live database to sit at the
    # *repository's actual current head* (computed from the Alembic scripts,
    # not from this file) AND requires that head to be a linear descendant
    # of this revision -- see `DemoDataManager._assert_revision`.
    minimum_alembic_revision: str
    namespace: str
    teacher_email: str = Field(min_length=1)
    interactive_student_email: str = Field(min_length=1)
    files: ManifestFiles
    material_directory: str
    content_files: list[str]
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_counts: ExpectedCounts


class TopicFixture(StrictModel):
    key: str
    name: str
    description: str
    parent: str | None


class MaterialFixture(StrictModel):
    key: str
    topic: str
    title: str
    source_file: str
    file_type: Literal["txt", "pdf"]


class BriefFixture(StrictModel):
    key: str
    topic: str
    material: str
    title: str
    content: str


class OptionFixture(StrictModel):
    content: str
    is_correct: bool


class QuestionFixture(StrictModel):
    key: str
    topic: str
    material: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    content: str
    points: int = Field(gt=0)
    is_ai_generated: Literal[False]
    options: list[OptionFixture]
    metadata: dict[str, Any]

    @model_validator(mode="after")
    def validate_answer_contract(self) -> "QuestionFixture":
        correct_count = sum(option.is_correct for option in self.options)
        if self.question_type == QuestionType.SINGLE_CHOICE:
            if len(self.options) < 2 or correct_count != 1:
                raise ValueError("single-choice questions require exactly one correct option")
        elif self.question_type == QuestionType.MULTIPLE_CHOICE:
            if len(self.options) < 3 or correct_count < 2:
                raise ValueError("multiple-choice questions require at least two correct options")
        elif self.question_type == QuestionType.MATCHING:
            pairs = self.metadata.get("pairs")
            if self.options or not isinstance(pairs, list) or len(pairs) < 2:
                raise ValueError("matching questions require at least two metadata pairs")
            if any(set(pair) != {"left", "right"} for pair in pairs):
                raise ValueError("matching pairs require left and right values")
        elif self.question_type == QuestionType.FILL_IN_BLANK:
            blanks = self.metadata.get("blanks")
            if self.options or not isinstance(blanks, list) or not blanks:
                raise ValueError("fill-in-blank questions require metadata blanks")
            for blank in blanks:
                if not isinstance(blank.get("blank_index"), int):
                    raise ValueError("blank_index must be an integer")
                answers = blank.get("acceptable_answers")
                if not isinstance(answers, list) or not answers:
                    raise ValueError("each blank requires acceptable answers")
        return self


class ExamFixture(StrictModel):
    key: str
    topic: str
    title: str
    description: str
    duration_minutes: int = Field(gt=0)
    is_published: bool
    questions: list[str]


class CardFixture(StrictModel):
    key: str
    front: str
    back: str
    order_index: int = Field(gt=0)


class DeckFixture(StrictModel):
    key: str
    topic: str
    material: str
    title: str
    description: str
    cards: list[CardFixture]


class StudentFixture(StrictModel):
    key: str
    email: str = Field(min_length=1)
    full_name: str
    interactive: bool


class SubmissionFixture(StrictModel):
    key: str
    exam: str
    student: str
    status: Literal["submitted", "in_progress"]
    correct_count: int = Field(ge=0, le=10)


class DemoFixture(StrictModel):
    root: Path
    manifest: DemoManifest
    topics: list[TopicFixture]
    materials: list[MaterialFixture]
    briefs: list[BriefFixture]
    questions: list[QuestionFixture]
    exams: list[ExamFixture]
    flashcards: list[DeckFixture]
    students: list[StudentFixture]
    submissions: list[SubmissionFixture]

    @model_validator(mode="after")
    def validate_references_and_counts(self) -> "DemoFixture":
        keyed_groups: dict[str, list[str]] = {
            "topic": [item.key for item in self.topics],
            "material": [item.key for item in self.materials],
            "brief": [item.key for item in self.briefs],
            "question": [item.key for item in self.questions],
            "exam": [item.key for item in self.exams],
            "deck": [item.key for item in self.flashcards],
            "card": [card.key for deck in self.flashcards for card in deck.cards],
            "student": [item.key for item in self.students],
            "submission": [item.key for item in self.submissions],
        }
        for group, keys in keyed_groups.items():
            duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
            if duplicates:
                raise ValueError(f"duplicate {group} keys: {', '.join(duplicates)}")

        topic_keys = set(keyed_groups["topic"])
        material_keys = set(keyed_groups["material"])
        question_keys = set(keyed_groups["question"])
        exam_keys = set(keyed_groups["exam"])
        student_keys = set(keyed_groups["student"])
        material_topic = {item.key: item.topic for item in self.materials}
        question_topic = {item.key: item.topic for item in self.questions}
        exam_topic = {item.key: item.topic for item in self.exams}
        question_by_key = {item.key: item for item in self.questions}

        for topic in self.topics:
            if topic.parent is not None and topic.parent not in topic_keys:
                raise ValueError(f"topic {topic.key} references missing parent {topic.parent}")
        for material in self.materials:
            if material.topic not in topic_keys:
                raise ValueError(f"material {material.key} references missing topic")
            validate_material_file(self.root / self.manifest.material_directory / material.source_file, material.file_type)
        for brief in self.briefs:
            if brief.topic not in topic_keys or brief.material not in material_keys:
                raise ValueError(f"brief {brief.key} has an invalid reference")
            if material_topic[brief.material] != brief.topic:
                raise ValueError(f"brief {brief.key} crosses topic ownership")
        for question_item in self.questions:
            if question_item.topic not in topic_keys or question_item.material not in material_keys:
                raise ValueError(f"question {question_item.key} has an invalid reference")
            if material_topic[question_item.material] != question_item.topic:
                raise ValueError(f"question {question_item.key} crosses material topic")
        assigned_questions: set[str] = set()
        for exam in self.exams:
            if exam.topic not in topic_keys or not exam.questions:
                raise ValueError(f"exam {exam.key} has an invalid topic or no questions")
            for question_key in exam.questions:
                if question_key not in question_keys:
                    raise ValueError(f"exam {exam.key} references missing question {question_key}")
                if question_key in assigned_questions:
                    raise ValueError(f"question {question_key} is assigned to multiple exams")
                assigned_questions.add(question_key)
                question_root = next(
                    topic.parent for topic in self.topics if topic.key == question_topic[question_key]
                )
                if question_root != exam.topic:
                    raise ValueError(f"exam {exam.key} references a question from another subject")
                if exam.is_published and question_by_key[question_key].question_type not in GRADEABLE_QUESTION_TYPES:
                    raise ValueError(f"published exam {exam.key} contains a currently ungradeable type")
        for deck in self.flashcards:
            if deck.topic not in topic_keys or deck.material not in material_keys:
                raise ValueError(f"deck {deck.key} has an invalid reference")
            if material_topic[deck.material] != deck.topic:
                raise ValueError(f"deck {deck.key} crosses material topic")
            if len(deck.cards) != 8:
                raise ValueError(f"deck {deck.key} must contain eight cards")
        for submission in self.submissions:
            if submission.exam not in exam_keys or submission.student not in student_keys:
                raise ValueError(f"submission {submission.key} has an invalid reference")
            exam = next(item for item in self.exams if item.key == submission.exam)
            if not exam.is_published:
                raise ValueError(f"submission {submission.key} references a draft exam")

        expected = self.manifest.expected_counts
        actual_counts = {
            "users": len(self.students),
            "topics": len(self.topics),
            "materials": len(self.materials),
            "topic_briefs": len(self.briefs),
            "questions": len(self.questions),
            "options": sum(len(item.options) for item in self.questions),
            "flashcard_decks": len(self.flashcards),
            "flashcards": sum(len(item.cards) for item in self.flashcards),
            "exams": len(self.exams),
            "submissions": len(self.submissions),
            "submission_answers": sum(
                len(next(exam.questions for exam in self.exams if exam.key == item.exam))
                for item in self.submissions if item.status == "submitted"
            ),
            "flashcard_progress": len(self.flashcards) * 4,
        }
        for field, actual in actual_counts.items():
            if actual != getattr(expected, field):
                raise ValueError(f"count mismatch for {field}: expected {getattr(expected, field)}, got {actual}")
        if expected.document_chunks != len(self.materials):
            raise ValueError("demo fixture requires one compact chunk per material")
        if len([item for item in self.topics if item.parent is None]) != 3:
            raise ValueError("demo fixture requires three root topics")
        if len([item for item in self.topics if item.parent is not None]) != 6:
            raise ValueError("demo fixture requires six lesson topics")
        if sum(item.status == "submitted" for item in self.submissions) != 12:
            raise ValueError("demo fixture requires twelve submitted attempts")
        if sum(item.status == "in_progress" for item in self.submissions) != 3:
            raise ValueError("demo fixture requires three in-progress attempts")
        if sum(item.interactive for item in self.students) != 1:
            raise ValueError("demo fixture requires exactly one interactive student")
        if exam_topic != {item.key: item.topic for item in self.exams}:
            raise AssertionError("unreachable exam topic mismatch")
        return self


def stable_uuid(namespace: str, entity_type: str, key: str) -> UUID:
    return uuid5(uuid5(UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8"), namespace), f"{entity_type}/{key}")


def compute_content_hash(root: Path, content_files: list[str]) -> str:
    digest = hashlib.sha256()
    for relative_name in sorted(content_files):
        relative = Path(relative_name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("fixture content path escapes the dataset root")
        path = root / relative
        if not path.is_file():
            raise ValueError(f"fixture content file is missing: {relative_name}")
        digest.update(relative_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_material_file(path: Path, file_type: str) -> None:
    if not path.is_file():
        raise ValueError(f"material source file is missing: {path.name}")
    if path.suffix.casefold() != f".{file_type}":
        raise ValueError(f"material extension does not match declared type: {path.name}")
    content = path.read_bytes()
    if not content:
        raise ValueError(f"material source file is empty: {path.name}")
    if file_type == "pdf" and not content.startswith(b"%PDF-"):
        raise ValueError(f"material is not a PDF by magic bytes: {path.name}")
    if file_type == "txt":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"material is not valid UTF-8 text: {path.name}") from exc


def _read_json(root: Path, relative_name: str) -> Any:
    relative = Path(relative_name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("fixture JSON path escapes the dataset root")
    return json.loads((root / relative).read_text(encoding="utf-8"))


def load_demo_fixture(root: Path = DEFAULT_FIXTURE_ROOT) -> DemoFixture:
    manifest = DemoManifest.model_validate(_read_json(root, "manifest.json"))
    actual_hash = compute_content_hash(root, manifest.content_files)
    if actual_hash != manifest.content_sha256:
        raise ValueError("fixture content hash does not match manifest")
    return DemoFixture(
        root=root,
        manifest=manifest,
        topics=[TopicFixture.model_validate(item) for item in _read_json(root, manifest.files.topics)],
        materials=[MaterialFixture.model_validate(item) for item in _read_json(root, manifest.files.materials)],
        briefs=[BriefFixture.model_validate(item) for item in _read_json(root, manifest.files.briefs)],
        questions=[QuestionFixture.model_validate(item) for item in _read_json(root, manifest.files.questions)],
        exams=[ExamFixture.model_validate(item) for item in _read_json(root, manifest.files.exams)],
        flashcards=[DeckFixture.model_validate(item) for item in _read_json(root, manifest.files.flashcards)],
        students=[StudentFixture.model_validate(item) for item in _read_json(root, manifest.files.students)],
        submissions=[SubmissionFixture.model_validate(item) for item in _read_json(root, manifest.files.submissions)],
    )
