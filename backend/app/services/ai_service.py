import time
import logging
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.material import StudyMaterial
from app.models.exam import Question, Option
from app.models.topic import Topic
from app.models.flashcard import FlashcardDeck, Flashcard
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.core.permissions import Permission, evaluate_owned_resource
from app.services.authorization_service import AuthorizationService
from app.services.material_processing import extract_and_chunk_material
import os

logger = logging.getLogger(__name__)


def mock_process_document_and_generate_questions(
    material_id: str,
    expected_owner_id: str,
    request_id: str,
):
    # Simulate processing time
    time.sleep(5)
    
    with SessionLocal() as db:
        material = db.scalar(
            select(StudyMaterial).where(
                StudyMaterial.id == UUID(material_id),
                StudyMaterial.uploader_id == UUID(expected_owner_id),
            )
        )
        if not material:
            return
            
        # 1. Process Document and Create Chunks
        try:
            content, chunks = extract_and_chunk_material(Path(material.file_path))
            for para in chunks:
                chunk = DocumentChunk(
                    material_id=material.id,
                    content=para,
                    embedding=[0.1] * 1536,
                )
                db.add(chunk)
            material.parsed_text = content
            db.commit()
        except Exception:
            logger.warning(
                "Background document processing failed request_id=%s",
                request_id,
            )
            material.ai_status = 'failed'
            db.commit()
            return
            
        # Mock generating questions
        q1 = Question(
            owner_id=material.uploader_id,
            material_id=material.id,
            content=f"What is the main topic of {material.title}?",
            is_ai_generated=True,
            points=1
        )
        db.add(q1)
        db.flush() # get q1.id
        
        db.add(Option(question_id=q1.id, content="AI", is_correct=True))
        db.add(Option(question_id=q1.id, content="Blockchain", is_correct=False))
        
        q2 = Question(
            owner_id=material.uploader_id,
            material_id=material.id,
            content="Which statement is true based on the document?",
            is_ai_generated=True,
            points=1
        )
        db.add(q2)
        db.flush()
        
        db.add(Option(question_id=q2.id, content="This is true", is_correct=True))
        db.add(Option(question_id=q2.id, content="This is false", is_correct=False))
        
        material.ai_status = "completed"
        db.commit()

def mock_generate_topic_kit(
    material_id: str,
    topic_id: str,
    expected_owner_id: str,
    actor_id: str,
    request_id: str,
):
    """
    Mock function to simulate AI generating a Topic Brief and Flashcards from a Study Material.
    """
    time.sleep(3) # Simulate AI processing time
    
    with SessionLocal() as db:
        owner_id = UUID(expected_owner_id)
        material = db.scalar(
            select(StudyMaterial).where(
                StudyMaterial.id == UUID(material_id),
                StudyMaterial.uploader_id == owner_id,
            )
        )
        topic = db.scalar(
            select(Topic).where(
                Topic.id == UUID(topic_id),
                Topic.owner_id == owner_id,
            )
        )
        actor = db.scalar(
            select(User)
            .where(User.id == UUID(actor_id))
            .with_for_update(read=True)
        )
        
        if not material or not topic or not actor:
            return
        if not evaluate_owned_resource(
            actor,
            Permission.UPDATE_OWNED_CONTENT,
            topic.owner_id,
        ).allowed:
            return

        # 1. Generate Topic Brief
        topic.brief_content = f"# {topic.name}\n\nĐây là bài tóm tắt kiến thức được tạo tự động bởi AI từ tài liệu: **{material.title}**.\n\n## 1. Khái niệm cơ bản\nNội dung khái niệm...\n\n## 2. Các điểm trọng tâm\n- Điểm 1\n- Điểm 2\n"
        topic.brief_ai_generated = True

        # 2. Generate Flashcard Deck
        deck = FlashcardDeck(
            topic_id=topic.id,
            material_id=material.id,
            title=f"Flashcards: {material.title}",
            description="Bộ thẻ ghi nhớ tự động tạo từ tài liệu."
        )
        db.add(deck)
        db.flush()

        # 3. Generate Flashcards
        cards_data = [
            ("AI là gì?", "Trí tuệ nhân tạo (AI) là khả năng của máy tính bắt chước các chức năng nhận thức của con người."),
            ("Spaced Repetition là gì?", "Kỹ thuật ôn tập ngắt quãng giúp ghi nhớ dài hạn bằng cách tăng dần thời gian giữa các lần ôn tập."),
            ("Mô hình Dữ liệu (Data Model) là gì?", "Cách cấu trúc và tổ chức dữ liệu trong cơ sở dữ liệu.")
        ]

        for i, (front, back) in enumerate(cards_data):
            card = Flashcard(
                deck_id=deck.id,
                front_content=front,
                back_content=back,
                order_index=i
            )
            db.add(card)

        AuthorizationService.commit_with_admin_override(
            db,
            actor=actor,
            permission=Permission.UPDATE_OWNED_CONTENT,
            entity_type="topic",
            entity_id=topic.id,
            owner_id=topic.owner_id,
            operation="generate",
            request_id=request_id,
        )
