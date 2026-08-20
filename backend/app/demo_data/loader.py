from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, cast
from uuid import UUID

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, selectinload

from app.core.file_storage import FileStorage
from app.core.security import get_password_hash
from app.demo_data.fixture import DATASET_ID, DemoFixture, stable_uuid
from app.models.document_chunk import DocumentChunk
from app.models.exam import Exam, Option, Question
from app.models.flashcard import Flashcard, FlashcardDeck, FlashcardProgress
from app.models.material import StudyMaterial
from app.models.submission import Submission, SubmissionAnswer
from app.models.topic import Topic
from app.models.topic_brief import TopicBrief
from app.models.user import User
from app.services.content_visibility import StudentContentVisibility
from app.services.grading_service import GradingService
from app.services.material_processing import MOCK_EMBEDDING, extract_and_chunk_material


LOCAL_DATABASE_HOSTS = {"127.0.0.1", "localhost", "::1"}
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
FIXED_START = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
LOCAL_DEMO_LOGIN_PASSWORD = "12345678"


class DemoDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlanItem:
    entity: str
    create: int
    unchanged: int
    conflict: int


@dataclass(frozen=True)
class DemoDataReport:
    dataset_id: str
    action: str
    items: tuple[PlanItem, ...] = ()
    counts: dict[str, int] = field(default_factory=dict)
    total_score_min: float | None = None
    total_score_max: float | None = None


def validate_demo_database_target(database_url: str, environment: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        raise DemoDataError("demo data requires PostgreSQL")
    if url.host not in LOCAL_DATABASE_HOSTS:
        raise DemoDataError("demo data is restricted to local PostgreSQL hosts")
    if not url.database:
        raise DemoDataError("database name is required")
    normalized_environment = environment.casefold()
    if normalized_environment not in {"development", "test"}:
        raise DemoDataError("demo data is restricted to development or test")
    if normalized_environment == "test" and not url.database.endswith("_test"):
        raise DemoDataError("test environment requires a database ending in _test")


def _ids(fixture: DemoFixture, entity: str, keys: Iterable[str]) -> list[UUID]:
    return [stable_uuid(fixture.manifest.namespace, entity, key) for key in keys]


class DemoDataManager:
    def __init__(
        self,
        fixture: DemoFixture,
        session: Session,
        storage: FileStorage,
        *,
        database_url: str,
        environment: str,
    ) -> None:
        validate_demo_database_target(database_url, environment)
        self.fixture = fixture
        self.session = session
        self.storage = storage

    def _assert_revision(self) -> None:
        """The database must be at the repo's real head, on a history the
        fixture is actually compatible with.

        Two checks, in order, because they fail closed for different
        reasons and the error should say which:

        1. The live database's `alembic_version` must equal the
           *repository's* current head -- computed live from the Alembic
           scripts directory, never from a value stored in this fixture.
           A stale database (behind head) or a diverged one (the scripts
           directory itself has more than one head, which would mean the
           repo's own migration history is broken) both fail here.
        2. `manifest.minimum_alembic_revision` must be a linear ancestor of
           that head -- walked one `down_revision` at a time with no branch
           point. This is deliberately weaker than an exact pin: a fixture
           with no schema dependency on anything past its minimum revision
           should not go stale every time an unrelated migration ships (the
           old exact-pin manifest field was already three heads behind by
           the time this changed). A merge point in the walk means the
           fixture's compatibility with post-merge history is unproven, so
           it is refused rather than assumed.
        """
        current = self.session.scalar(text("SELECT version_num FROM alembic_version"))
        script = ScriptDirectory.from_config(
            AlembicConfig(str(_BACKEND_ROOT / "alembic.ini"))
        )
        heads = script.get_heads()
        if len(heads) != 1:
            raise DemoDataError(
                "repository Alembic history has diverged heads "
                f"{sorted(heads)!r}; refusing to load demo data"
            )
        repository_head = heads[0]
        if current != repository_head:
            raise DemoDataError(
                f"database is at revision {current!r}, not the repository's "
                f"current Alembic head {repository_head!r}; run "
                "`alembic upgrade head` first"
            )

        minimum_revision = self.fixture.manifest.minimum_alembic_revision
        revision: str | None = repository_head
        visited: set[str] = set()
        while revision is not None:
            if revision == minimum_revision:
                return
            if revision in visited:
                raise DemoDataError(
                    "cycle detected walking Alembic history from "
                    f"{repository_head!r}"
                )
            visited.add(revision)
            script_revision = script.get_revision(revision)
            down_revision = script_revision.down_revision if script_revision else None
            # Alembic represents a merge point's `down_revision` as a
            # sequence (a `tuple` at runtime; the type stubs also allow
            # `list`), never as a bare revision id, so any non-`str`
            # non-`None` value here means multiple parents.
            if down_revision is not None and not isinstance(down_revision, str):
                raise DemoDataError(
                    f"revision {revision!r} has multiple parents "
                    f"{down_revision!r} (a merge point); the fixture's "
                    "minimum_alembic_revision must be a linear ancestor of "
                    "head"
                )
            revision = down_revision
        raise DemoDataError(
            f"fixture minimum_alembic_revision {minimum_revision!r} is not "
            f"an ancestor of the repository head {repository_head!r}"
        )

    def _teacher(self) -> User:
        teacher = self.session.scalar(
            select(User).where(User.email == self.fixture.manifest.teacher_email)
        )
        if teacher is None or teacher.role != "teacher":
            raise DemoDataError("the canonical teacher account is missing or has the wrong role")
        return teacher

    def _interactive_student(self) -> User:
        student = self.session.scalar(
            select(User).where(User.email == self.fixture.manifest.interactive_student_email)
        )
        if student is None or student.role != "student":
            raise DemoDataError("the canonical interactive student is missing or has the wrong role")
        return student

    def _canonical_account_specs(self) -> tuple[tuple[str, str, str], ...]:
        interactive_student = next(
            item for item in self.fixture.students if item.interactive
        )
        return (
            ("admin", "admin@example.com", "Demo Administrator"),
            (
                "teacher",
                self.fixture.manifest.teacher_email,
                "Demo Teacher",
            ),
            (
                "student",
                interactive_student.email,
                interactive_student.full_name,
            ),
        )

    def _canonical_account_plan(self) -> PlanItem:
        create = 0
        unchanged = 0
        conflict = 0
        for role, email, full_name in self._canonical_account_specs():
            expected_id = stable_uuid(
                self.fixture.manifest.namespace,
                "account",
                role,
            )
            account = self.session.scalar(select(User).where(User.email == email))
            if account is None:
                create += 1
            elif (
                account.id,
                account.role,
                account.full_name,
            ) == (expected_id, role, full_name):
                unchanged += 1
            else:
                conflict += 1
        return PlanItem(
            entity="canonical_accounts",
            create=create,
            unchanged=unchanged,
            conflict=conflict,
        )

    def _ensure_canonical_accounts(self) -> dict[str, User]:
        accounts: dict[str, User] = {}
        for role, email, full_name in self._canonical_account_specs():
            expected_id = stable_uuid(
                self.fixture.manifest.namespace,
                "account",
                role,
            )
            account = self.session.scalar(select(User).where(User.email == email))
            if account is None:
                account = User(
                    id=expected_id,
                    email=email,
                    password_hash=get_password_hash(LOCAL_DEMO_LOGIN_PASSWORD),
                    full_name=full_name,
                    role=role,
                )
                self.session.add(account)
                self.session.flush()
            elif (
                account.id,
                account.role,
                account.full_name,
            ) != (expected_id, role, full_name):
                raise DemoDataError(
                    f"canonical {role} account conflicts with demo-standard-v1"
                )
            accounts[role] = account
        return accounts

    def _identity_groups(self) -> dict[str, tuple[type[Any], list[UUID]]]:
        return {
            "topics": (Topic, _ids(self.fixture, "topic", (item.key for item in self.fixture.topics))),
            "materials": (StudyMaterial, _ids(self.fixture, "material", (item.key for item in self.fixture.materials))),
            "document_chunks": (DocumentChunk, _ids(self.fixture, "chunk", (item.key for item in self.fixture.materials))),
            "topic_briefs": (TopicBrief, _ids(self.fixture, "brief", (item.key for item in self.fixture.briefs))),
            "exams": (Exam, _ids(self.fixture, "exam", (item.key for item in self.fixture.exams))),
            "questions": (Question, _ids(self.fixture, "question", (item.key for item in self.fixture.questions))),
            "options": (
                Option,
                [
                    stable_uuid(self.fixture.manifest.namespace, "option", f"{question.key}/{index}")
                    for question in self.fixture.questions
                    for index, _ in enumerate(question.options, start=1)
                ],
            ),
            "flashcard_decks": (FlashcardDeck, _ids(self.fixture, "deck", (item.key for item in self.fixture.flashcards))),
            "flashcards": (
                Flashcard,
                _ids(
                    self.fixture,
                    "card",
                    (card.key for deck in self.fixture.flashcards for card in deck.cards),
                ),
            ),
            "submissions": (Submission, _ids(self.fixture, "submission", (item.key for item in self.fixture.submissions))),
            "submission_answers": (
                SubmissionAnswer,
                [
                    stable_uuid(self.fixture.manifest.namespace, "answer", f"{submission.key}/{question_key}")
                    for submission in self.fixture.submissions
                    if submission.status == "submitted"
                    for question_key in next(exam.questions for exam in self.fixture.exams if exam.key == submission.exam)
                ],
            ),
            "flashcard_progress": (
                FlashcardProgress,
                [
                    stable_uuid(self.fixture.manifest.namespace, "progress", f"{deck.key}/{student.key}")
                    for deck in self.fixture.flashcards
                    for student in self.fixture.students[:4]
                ],
            ),
            "analytics_students": (
                User,
                _ids(
                    self.fixture,
                    "student",
                    (item.key for item in self.fixture.students if not item.interactive),
                ),
            ),
        }

    def plan(self) -> DemoDataReport:
        self._assert_revision()
        items: list[PlanItem] = []
        for entity, (model, ids) in self._identity_groups().items():
            existing = set(self.session.scalars(select(model.id).where(model.id.in_(ids))).all())
            items.append(
                PlanItem(
                    entity=entity,
                    create=len(ids) - len(existing),
                    unchanged=len(existing),
                    conflict=0,
                )
            )
        dataset_has_existing_rows = any(item.unchanged for item in items)
        items.append(self._canonical_account_plan())
        if dataset_has_existing_rows:
            try:
                self.verify()
            except DemoDataError:
                items = [
                    PlanItem(
                        entity=item.entity,
                        create=item.create,
                        unchanged=0,
                        conflict=item.unchanged,
                    )
                    for item in items
                ]
        return DemoDataReport(dataset_id=DATASET_ID, action="plan", items=tuple(items))

    def apply(self) -> DemoDataReport:
        plan = self.plan()
        if any(item.conflict for item in plan.items):
            raise DemoDataError("dataset-owned rows conflict with the fixture; reset explicitly before applying")
        if all(item.create == 0 for item in plan.items):
            return self.verify(action="apply")

        stored_paths: list[str] = []
        try:
            with self.session.begin_nested():
                accounts = self._ensure_canonical_accounts()
                teacher = accounts["teacher"]
                interactive_student = accounts["student"]
                students = self._create_students(interactive_student)
                topics = self._create_topics(teacher)
                materials = self._create_materials(teacher, topics, stored_paths)
                exams = self._create_exams(teacher, topics)
                questions = self._create_questions(teacher, topics, materials, exams)
                self._create_briefs(topics, materials)
                decks = self._create_flashcards(topics, materials)
                self._create_submissions(students, exams, questions)
                self._create_progress(students, decks)
            self.session.commit()
        except Exception:
            self.session.rollback()
            for stored_path in stored_paths:
                self.storage.delete(stored_path)
            raise
        return self.verify(action="apply")

    def _create_students(self, interactive_student: User) -> dict[str, User]:
        students = {"student-primary": interactive_student}
        for item in self.fixture.students:
            if item.interactive:
                if item.email != interactive_student.email:
                    raise DemoDataError("interactive student fixture does not match the canonical account")
                continue
            student_id = stable_uuid(self.fixture.manifest.namespace, "student", item.key)
            existing_email = self.session.scalar(select(User).where(User.email == item.email))
            if existing_email is not None and existing_email.id != student_id:
                raise DemoDataError("analytics student email is already used by another record")
            student = User(
                id=student_id,
                email=item.email,
                full_name=item.full_name,
                role="student",
                password_hash=get_password_hash(secrets.token_urlsafe(32)),
            )
            self.session.add(student)
            students[item.key] = student
        self.session.flush()
        return students

    def _create_topics(self, teacher: User) -> dict[str, Topic]:
        topics: dict[str, Topic] = {}
        remaining = list(self.fixture.topics)
        while remaining:
            progressed = False
            for item in remaining[:]:
                if item.parent is not None and item.parent not in topics:
                    continue
                topic = Topic(
                    id=stable_uuid(self.fixture.manifest.namespace, "topic", item.key),
                    owner_id=teacher.id,
                    name=item.name,
                    description=item.description,
                    parent_id=topics[item.parent].id if item.parent else None,
                    brief_ai_generated=False,
                )
                self.session.add(topic)
                topics[item.key] = topic
                remaining.remove(item)
                progressed = True
            if not progressed:
                raise DemoDataError("topic dependency ordering could not be resolved")
        self.session.flush()
        return topics

    def _create_materials(
        self,
        teacher: User,
        topics: dict[str, Topic],
        stored_paths: list[str],
    ) -> dict[str, StudyMaterial]:
        materials: dict[str, StudyMaterial] = {}
        for item in self.fixture.materials:
            source = self.fixture.root / self.fixture.manifest.material_directory / item.source_file
            stored_path = self.storage.save(item.source_file, source.read_bytes())
            stored_paths.append(stored_path)
            resolved = self.storage.resolve_for_read(stored_path)
            parsed_text, chunks = extract_and_chunk_material(resolved)
            if len(chunks) != 1:
                raise DemoDataError("each compact demo material must produce exactly one chunk")
            material = StudyMaterial(
                id=stable_uuid(self.fixture.manifest.namespace, "material", item.key),
                uploader_id=teacher.id,
                topic_id=topics[item.topic].id,
                title=item.title,
                file_type=item.file_type,
                file_path=stored_path,
                parsed_text=parsed_text,
                ai_status="completed",
            )
            self.session.add(material)
            materials[item.key] = material
            self.session.flush()
            self.session.add(
                DocumentChunk(
                    id=stable_uuid(self.fixture.manifest.namespace, "chunk", item.key),
                    material_id=material.id,
                    content=chunks[0],
                    embedding=MOCK_EMBEDDING,
                )
            )
        self.session.flush()
        return materials

    def _create_exams(self, teacher: User, topics: dict[str, Topic]) -> dict[str, Exam]:
        exams: dict[str, Exam] = {}
        for index, item in enumerate(self.fixture.exams):
            exam = Exam(
                id=stable_uuid(self.fixture.manifest.namespace, "exam", item.key),
                creator_id=teacher.id,
                topic_id=topics[item.topic].id,
                title=item.title,
                description=item.description,
                duration_minutes=item.duration_minutes,
                is_published=item.is_published,
                created_at=FIXED_START + timedelta(days=index),
            )
            self.session.add(exam)
            exams[item.key] = exam
        self.session.flush()
        return exams

    def _create_questions(
        self,
        teacher: User,
        topics: dict[str, Topic],
        materials: dict[str, StudyMaterial],
        exams: dict[str, Exam],
    ) -> dict[str, Question]:
        exam_for_question = {
            question_key: exam.key
            for exam in self.fixture.exams
            for question_key in exam.questions
        }
        questions: dict[str, Question] = {}
        for item in self.fixture.questions:
            question_model = Question(
                id=stable_uuid(self.fixture.manifest.namespace, "question", item.key),
                owner_id=teacher.id,
                exam_id=(
                    exams[exam_for_question[item.key]].id
                    if item.key in exam_for_question else None
                ),
                topic_id=topics[item.topic].id,
                material_id=materials[item.material].id,
                question_type=item.question_type,
                difficulty=item.difficulty,
                content=item.content,
                metadata_json=item.metadata,
                is_ai_generated=False,
                points=item.points,
            )
            self.session.add(question_model)
            for index, option in enumerate(item.options, start=1):
                question_model.options.append(
                    Option(
                        id=stable_uuid(
                            self.fixture.manifest.namespace,
                            "option",
                            f"{item.key}/{index}",
                        ),
                        content=option.content,
                        is_correct=option.is_correct,
                    )
                )
            questions[item.key] = question_model
        self.session.flush()
        return questions

    def _create_briefs(
        self,
        topics: dict[str, Topic],
        materials: dict[str, StudyMaterial],
    ) -> None:
        for item in self.fixture.briefs:
            setattr(topics[item.topic], "brief_content", item.content)
            setattr(topics[item.topic], "brief_ai_generated", False)
            self.session.add(
                TopicBrief(
                    id=stable_uuid(self.fixture.manifest.namespace, "brief", item.key),
                    topic_id=topics[item.topic].id,
                    material_id=materials[item.material].id,
                    title=item.title,
                    content=item.content,
                    is_ai_generated=False,
                )
            )
        self.session.flush()

    def _create_flashcards(
        self,
        topics: dict[str, Topic],
        materials: dict[str, StudyMaterial],
    ) -> dict[str, tuple[FlashcardDeck, list[Flashcard]]]:
        decks: dict[str, tuple[FlashcardDeck, list[Flashcard]]] = {}
        for item in self.fixture.flashcards:
            deck = FlashcardDeck(
                id=stable_uuid(self.fixture.manifest.namespace, "deck", item.key),
                topic_id=topics[item.topic].id,
                material_id=materials[item.material].id,
                title=item.title,
                description=item.description,
            )
            cards = [
                Flashcard(
                    id=stable_uuid(self.fixture.manifest.namespace, "card", card.key),
                    deck_id=deck.id,
                    front_content=card.front,
                    back_content=card.back,
                    order_index=card.order_index,
                )
                for card in item.cards
            ]
            deck.flashcards.extend(cards)
            self.session.add(deck)
            decks[item.key] = (deck, cards)
        self.session.flush()
        return decks

    @staticmethod
    def _answer_for(question: Question, correct: bool) -> dict[str, Any]:
        if question.question_type.value == "SINGLE_CHOICE":
            options = list(cast(Any, question.options))
            chosen = next(
                item for item in options if item.is_correct is bool(correct)
            )
            # The canonical single-choice shape: one id, not a list. The
            # grader refuses a multi-id payload for this type on purpose.
            return {"selected_option_id": str(chosen.id)}
        if question.question_type.value == "MULTIPLE_CHOICE":
            options = list(cast(Any, question.options))
            selected = [str(item.id) for item in options if item.is_correct]
            if not correct:
                selected = [str(next(item.id for item in options if not item.is_correct))]
            return {"selected_option_ids": selected}
        if question.question_type.value == "MATCHING":
            pairs = cast(dict[str, Any], question.metadata_json)["pairs"]
            if correct:
                return {"matches": pairs}
            return {"matches": [{"left": item["left"], "right": "Incorrect"} for item in pairs]}
        if question.question_type.value == "FILL_IN_BLANK":
            blanks = cast(dict[str, Any], question.metadata_json)["blanks"]
            return {
                "blanks": {
                    str(item["blank_index"]): (
                        item["acceptable_answers"][0] if correct else "incorrect"
                    )
                    for item in blanks
                }
            }
        return {}

    def _create_submissions(
        self,
        students: dict[str, User],
        exams: dict[str, Exam],
        questions: dict[str, Question],
    ) -> None:
        fixture_exams = {item.key: item for item in self.fixture.exams}
        for index, item in enumerate(self.fixture.submissions):
            start_time = FIXED_START + timedelta(days=index, hours=1)
            submission = Submission(
                id=stable_uuid(self.fixture.manifest.namespace, "submission", item.key),
                exam_id=exams[item.exam].id,
                student_id=students[item.student].id,
                start_time=start_time,
                status=item.status,
                total_score=0.0,
            )
            self.session.add(submission)
            if item.status == "submitted":
                total = 0.0
                for question_index, question_key in enumerate(
                    fixture_exams[item.exam].questions
                ):
                    question_model = questions[question_key]
                    answer_data = self._answer_for(
                        question_model,
                        correct=question_index < item.correct_count,
                    )
                    points = GradingService.grade_question(question_model, answer_data)
                    total += points
                    self.session.add(
                        SubmissionAnswer(
                            id=stable_uuid(
                                self.fixture.manifest.namespace,
                                "answer",
                                f"{item.key}/{question_key}",
                            ),
                            submission_id=submission.id,
                            question_id=question_model.id,
                            answer_data=answer_data,
                            is_correct=points == question_model.points,
                            points_awarded=points,
                        )
                    )
                setattr(submission, "end_time", start_time + timedelta(minutes=25 + index % 12))
                setattr(submission, "total_score", total)
        self.session.flush()

    def _create_progress(
        self,
        students: dict[str, User],
        decks: dict[str, tuple[FlashcardDeck, list[Flashcard]]],
    ) -> None:
        states = [
            (0, timedelta(minutes=10)),
            (1, timedelta(days=1)),
            (3, timedelta(days=7)),
            (5, timedelta(days=30)),
        ]
        progress_students = self.fixture.students[:4]
        for deck_item in self.fixture.flashcards:
            _, cards = decks[deck_item.key]
            for index, student_item in enumerate(progress_students):
                level, interval = states[index]
                reviewed_at = FIXED_START + timedelta(days=10 + index)
                self.session.add(
                    FlashcardProgress(
                        id=stable_uuid(
                            self.fixture.manifest.namespace,
                            "progress",
                            f"{deck_item.key}/{student_item.key}",
                        ),
                        student_id=students[student_item.key].id,
                        flashcard_id=cards[index].id,
                        box_level=level,
                        last_reviewed_at=reviewed_at,
                        next_review_at=reviewed_at + interval,
                    )
                )
        self.session.flush()

    def verify(self, action: str = "verify") -> DemoDataReport:
        self._assert_revision()
        teacher = self._teacher()
        interactive_student = self._interactive_student()
        account_plan = self._canonical_account_plan()
        if account_plan.unchanged != 3:
            raise DemoDataError("canonical account verification failed")
        groups = self._identity_groups()
        counts: dict[str, int] = {"canonical_accounts": 3}
        for entity, (model, ids) in groups.items():
            count = self.session.scalar(
                select(func.count()).select_from(model).where(model.id.in_(ids))
            )
            counts[entity] = int(count or 0)
            if counts[entity] != len(ids):
                raise DemoDataError(f"dataset verification failed for {entity}")

        topic_ids = groups["topics"][1]
        question_ids = groups["questions"][1]
        material_ids = groups["materials"][1]
        exam_ids = groups["exams"][1]
        if self.session.scalar(
            select(func.count()).select_from(Topic).where(
                Topic.id.in_(topic_ids), Topic.owner_id == teacher.id
            )
        ) != len(topic_ids):
            raise DemoDataError("topic ownership verification failed")
        if self.session.scalar(
            select(func.count()).select_from(Question).where(
                Question.id.in_(question_ids),
                Question.owner_id == teacher.id,
                Question.is_ai_generated.is_(False),
            )
        ) != len(question_ids):
            raise DemoDataError("question ownership or authorship verification failed")
        self._verify_exact_content(teacher)
        materials = self.session.scalars(
            select(StudyMaterial).where(
                StudyMaterial.id.in_(material_ids),
                StudyMaterial.uploader_id == teacher.id,
                StudyMaterial.ai_status == "completed",
            )
        ).all()
        if len(materials) != len(material_ids):
            raise DemoDataError("material ownership or processing verification failed")
        for material in materials:
            self.storage.resolve_for_read(cast(str, material.file_path))
            if not material.parsed_text:
                raise DemoDataError("material parsed text is missing")

        visible_exam_count = self.session.scalar(
            select(func.count()).select_from(
                StudentContentVisibility.exam_statement().where(Exam.id.in_(exam_ids)).subquery()
            )
        )
        if visible_exam_count != 3:
            raise DemoDataError("student published-exam visibility verification failed")

        submissions = self.session.scalars(
            select(Submission)
            .options(
                selectinload(Submission.answers),
                selectinload(Submission.exam)
                .selectinload(Exam.questions)
                .selectinload(Question.options),
            )
            .where(Submission.id.in_(groups["submissions"][1]))
        ).all()
        submitted_scores: list[float] = []
        for submission in submissions:
            if submission.status != "submitted":
                continue
            expected_total = 0.0
            question_map = {question.id: question for question in submission.exam.questions}
            for answer in submission.answers:
                expected_points = GradingService.grade_question(
                    question_map[answer.question_id], answer.answer_data or {}
                )
                if expected_points != answer.points_awarded:
                    raise DemoDataError("submission answer score verification failed")
                expected_total += expected_points
            if expected_total != submission.total_score:
                raise DemoDataError("submission total score verification failed")
            submitted_scores.append(expected_total)
        if len(submitted_scores) != 12 or len(set(submitted_scores)) < 4:
            raise DemoDataError("submission score distribution verification failed")
        if interactive_student.id != next(
            item.student_id
            for item in submissions
            if item.student_id == interactive_student.id
        ):
            raise DemoDataError("interactive student submission verification failed")

        return DemoDataReport(
            dataset_id=DATASET_ID,
            action=action,
            counts=counts,
            total_score_min=min(submitted_scores),
            total_score_max=max(submitted_scores),
        )

    def _verify_exact_content(self, teacher: User) -> None:
        namespace = self.fixture.manifest.namespace
        topic_models: dict[UUID, Topic] = {
            cast(UUID, model.id): model
            for model in self.session.scalars(
                select(Topic).where(
                    Topic.id.in_(
                        _ids(self.fixture, "topic", (item.key for item in self.fixture.topics))
                    )
                )
            ).all()
        }
        topic_ids = {
            item.key: stable_uuid(namespace, "topic", item.key)
            for item in self.fixture.topics
        }
        brief_by_topic = {item.topic: item.content for item in self.fixture.briefs}
        for topic_item in self.fixture.topics:
            model = topic_models[topic_ids[topic_item.key]]
            expected_parent = topic_ids[topic_item.parent] if topic_item.parent else None
            actual = (
                cast(str, model.name),
                cast(str | None, model.description),
                cast(UUID | None, model.parent_id),
                cast(UUID | None, model.owner_id),
                cast(str | None, model.brief_content),
                bool(model.brief_ai_generated),
            )
            expected = (
                topic_item.name,
                topic_item.description,
                expected_parent,
                teacher.id,
                brief_by_topic.get(topic_item.key),
                False,
            )
            if actual != expected:
                raise DemoDataError(f"topic content drift detected for {topic_item.key}")

        material_ids = {
            item.key: stable_uuid(namespace, "material", item.key)
            for item in self.fixture.materials
        }
        material_models: dict[UUID, StudyMaterial] = {
            cast(UUID, model.id): model
            for model in self.session.scalars(
                select(StudyMaterial).where(StudyMaterial.id.in_(material_ids.values()))
            ).all()
        }
        for material_item in self.fixture.materials:
            model = material_models[material_ids[material_item.key]]
            if (
                cast(str, model.title),
                cast(str, model.file_type),
                cast(UUID, model.topic_id),
                cast(UUID, model.uploader_id),
                cast(str, model.ai_status),
            ) != (material_item.title, material_item.file_type, topic_ids[material_item.topic], teacher.id, "completed"):
                raise DemoDataError(f"material content drift detected for {material_item.key}")
            stored = self.storage.resolve_for_read(cast(str, model.file_path))
            source = self.fixture.root / self.fixture.manifest.material_directory / material_item.source_file
            if stored.read_bytes() != source.read_bytes():
                raise DemoDataError(f"stored material drift detected for {material_item.key}")
            extracted, chunks = extract_and_chunk_material(stored)
            if cast(str, model.parsed_text) != extracted or len(chunks) != 1:
                raise DemoDataError(f"parsed material drift detected for {material_item.key}")
            chunk = self.session.get(
                DocumentChunk,
                stable_uuid(namespace, "chunk", material_item.key),
            )
            if chunk is None or cast(str, chunk.content) != chunks[0]:
                raise DemoDataError(f"material chunk drift detected for {material_item.key}")

        exam_ids = {
            item.key: stable_uuid(namespace, "exam", item.key)
            for item in self.fixture.exams
        }
        exam_models: dict[UUID, Exam] = {
            cast(UUID, model.id): model
            for model in self.session.scalars(
                select(Exam).where(Exam.id.in_(exam_ids.values()))
            ).all()
        }
        exam_for_question = {
            question_key: item.key
            for item in self.fixture.exams
            for question_key in item.questions
        }
        for exam_item in self.fixture.exams:
            model = exam_models[exam_ids[exam_item.key]]
            if (
                cast(str, model.title),
                cast(str, model.description),
                int(model.duration_minutes),
                bool(model.is_published),
                cast(UUID, model.topic_id),
                cast(UUID, model.creator_id),
            ) != (
                exam_item.title,
                exam_item.description,
                exam_item.duration_minutes,
                exam_item.is_published,
                topic_ids[exam_item.topic],
                teacher.id,
            ):
                raise DemoDataError(f"exam content drift detected for {exam_item.key}")

        question_ids = {
            item.key: stable_uuid(namespace, "question", item.key)
            for item in self.fixture.questions
        }
        question_models: dict[UUID, Question] = {
            cast(UUID, model.id): model
            for model in self.session.scalars(
                select(Question)
                .options(selectinload(Question.options))
                .where(Question.id.in_(question_ids.values()))
            ).all()
        }
        for question_item in self.fixture.questions:
            model = question_models[question_ids[question_item.key]]
            expected_exam = (
                exam_ids[exam_for_question[question_item.key]]
                if question_item.key in exam_for_question else None
            )
            if (
                cast(str, model.content),
                model.question_type,
                model.difficulty,
                int(model.points),
                cast(dict[str, Any], model.metadata_json) or {},
                cast(UUID, model.topic_id),
                cast(UUID, model.material_id),
                cast(UUID | None, model.exam_id),
            ) != (
                question_item.content,
                question_item.question_type,
                question_item.difficulty,
                question_item.points,
                question_item.metadata,
                topic_ids[question_item.topic],
                material_ids[question_item.material],
                expected_exam,
            ):
                raise DemoDataError(f"question content drift detected for {question_item.key}")
            actual_options = [
                (option.id, cast(str, option.content), bool(option.is_correct))
                for option in cast(list[Option], model.options)
            ]
            expected_options = [
                (
                    stable_uuid(namespace, "option", f"{question_item.key}/{index}"),
                    option.content,
                    option.is_correct,
                )
                for index, option in enumerate(question_item.options, start=1)
            ]
            if actual_options != expected_options:
                raise DemoDataError(f"question option drift detected for {question_item.key}")

        brief_models: dict[UUID, TopicBrief] = {
            cast(UUID, model.id): model
            for model in self.session.scalars(
                select(TopicBrief).where(
                    TopicBrief.id.in_(
                        _ids(self.fixture, "brief", (item.key for item in self.fixture.briefs))
                    )
                )
            ).all()
        }
        for brief_item in self.fixture.briefs:
            model = brief_models[stable_uuid(namespace, "brief", brief_item.key)]
            if (
                cast(str, model.title),
                cast(str, model.content),
                cast(UUID, model.topic_id),
                cast(UUID, model.material_id),
                bool(model.is_ai_generated),
            ) != (
                brief_item.title,
                brief_item.content,
                topic_ids[brief_item.topic],
                material_ids[brief_item.material],
                False,
            ):
                raise DemoDataError(f"brief content drift detected for {brief_item.key}")

        deck_ids = {
            item.key: stable_uuid(namespace, "deck", item.key)
            for item in self.fixture.flashcards
        }
        deck_models: dict[UUID, FlashcardDeck] = {
            cast(UUID, model.id): model
            for model in self.session.scalars(
                select(FlashcardDeck)
                .options(selectinload(FlashcardDeck.flashcards))
                .where(FlashcardDeck.id.in_(deck_ids.values()))
            ).all()
        }
        for deck_item in self.fixture.flashcards:
            model = deck_models[deck_ids[deck_item.key]]
            if (
                cast(str, model.title),
                cast(str, model.description),
                cast(UUID, model.topic_id),
                cast(UUID, model.material_id),
            ) != (
                deck_item.title,
                deck_item.description,
                topic_ids[deck_item.topic],
                material_ids[deck_item.material],
            ):
                raise DemoDataError(f"flashcard deck drift detected for {deck_item.key}")
            actual_cards = [
                (
                    card.id,
                    cast(str, card.front_content),
                    cast(str, card.back_content),
                    int(card.order_index),
                )
                for card in sorted(
                    cast(list[Flashcard], model.flashcards),
                    key=lambda card: int(card.order_index),
                )
            ]
            expected_cards = [
                (
                    stable_uuid(namespace, "card", card.key),
                    card.front,
                    card.back,
                    card.order_index,
                )
                for card in deck_item.cards
            ]
            if actual_cards != expected_cards:
                raise DemoDataError(f"flashcard content drift detected for {deck_item.key}")

        for student_item in self.fixture.students:
            if student_item.interactive:
                student = self.session.scalar(select(User).where(User.email == student_item.email))
            else:
                student = self.session.get(
                    User, stable_uuid(namespace, "student", student_item.key)
                )
            if student is None or (
                cast(str, student.email), cast(str, student.full_name), cast(str, student.role)
            ) != (student_item.email, student_item.full_name, "student"):
                raise DemoDataError(f"student content drift detected for {student_item.key}")

    def _assert_no_external_dependencies(self) -> None:
        groups = self._identity_groups()
        topic_ids = groups["topics"][1]
        material_ids = groups["materials"][1]
        exam_ids = groups["exams"][1]
        question_ids = groups["questions"][1]
        option_ids = groups["options"][1]
        chunk_ids = groups["document_chunks"][1]
        brief_ids = groups["topic_briefs"][1]
        deck_ids = groups["flashcard_decks"][1]
        card_ids = groups["flashcards"][1]
        dataset_submission_ids = groups["submissions"][1]
        answer_ids = groups["submission_answers"][1]
        dataset_progress_ids = groups["flashcard_progress"][1]
        checks = [
            select(func.count()).select_from(Topic).where(
                Topic.parent_id.in_(topic_ids), Topic.id.not_in(topic_ids)
            ),
            select(func.count()).select_from(StudyMaterial).where(
                StudyMaterial.topic_id.in_(topic_ids),
                StudyMaterial.id.not_in(material_ids),
            ),
            select(func.count()).select_from(Exam).where(
                Exam.topic_id.in_(topic_ids), Exam.id.not_in(exam_ids)
            ),
            select(func.count()).select_from(Question).where(
                or_(
                    Question.exam_id.in_(exam_ids),
                    Question.topic_id.in_(topic_ids),
                    Question.material_id.in_(material_ids),
                ),
                Question.id.not_in(question_ids),
            ),
            select(func.count()).select_from(Option).where(
                Option.question_id.in_(question_ids), Option.id.not_in(option_ids)
            ),
            select(func.count()).select_from(DocumentChunk).where(
                DocumentChunk.material_id.in_(material_ids),
                DocumentChunk.id.not_in(chunk_ids),
            ),
            select(func.count()).select_from(TopicBrief).where(
                or_(
                    TopicBrief.topic_id.in_(topic_ids),
                    TopicBrief.material_id.in_(material_ids),
                ),
                TopicBrief.id.not_in(brief_ids),
            ),
            select(func.count()).select_from(FlashcardDeck).where(
                or_(
                    FlashcardDeck.topic_id.in_(topic_ids),
                    FlashcardDeck.material_id.in_(material_ids),
                ),
                FlashcardDeck.id.not_in(deck_ids),
            ),
            select(func.count()).select_from(Flashcard).where(
                Flashcard.deck_id.in_(deck_ids), Flashcard.id.not_in(card_ids)
            ),
            select(func.count()).select_from(Submission).where(
                Submission.exam_id.in_(exam_ids),
                Submission.id.not_in(dataset_submission_ids),
            ),
            select(func.count()).select_from(SubmissionAnswer).where(
                or_(
                    SubmissionAnswer.submission_id.in_(dataset_submission_ids),
                    SubmissionAnswer.question_id.in_(question_ids),
                ),
                SubmissionAnswer.id.not_in(answer_ids),
            ),
            select(func.count()).select_from(FlashcardProgress).where(
                FlashcardProgress.flashcard_id.in_(card_ids),
                FlashcardProgress.id.not_in(dataset_progress_ids),
            ),
        ]
        if any(self.session.scalar(statement) for statement in checks):
            raise DemoDataError(
                "reset refused because non-dataset learning records reference demo content"
            )

    def reset(self, confirmation: str) -> DemoDataReport:
        if confirmation != DATASET_ID:
            raise DemoDataError("reset confirmation does not match the dataset ID")
        self._assert_revision()
        self._assert_no_external_dependencies()
        groups = self._identity_groups()
        material_ids = groups["materials"][1]
        stored_paths = self.session.scalars(
            select(StudyMaterial.file_path).where(StudyMaterial.id.in_(material_ids))
        ).all()
        deletion_order = [
            "submission_answers",
            "submissions",
            "flashcard_progress",
            "flashcards",
            "flashcard_decks",
            "options",
            "questions",
            "exams",
            "topic_briefs",
            "document_chunks",
            "materials",
            "topics",
            "analytics_students",
        ]
        deleted: dict[str, int] = {}
        try:
            with self.session.begin_nested():
                for entity in deletion_order:
                    model, ids = groups[entity]
                    result = self.session.execute(delete(model).where(model.id.in_(ids)))
                    deleted[entity] = int(getattr(result, "rowcount", 0) or 0)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        for stored_path in stored_paths:
            self.storage.delete(stored_path)
        return DemoDataReport(dataset_id=DATASET_ID, action="reset", counts=deleted)
