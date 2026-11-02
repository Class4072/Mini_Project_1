import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Float,
    Integer,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import settings


class TravelSpot(Base):
    """여행지 / 관광지 / 맛집 / 카페 등 여행 스팟 정보 및 벡터 임베딩 모델"""
    __tablename__ = "travel_spots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)  # e.g., '강원도 강릉시', '제주특별자치도 제주시'
    address = Column(String(500), nullable=True)
    category = Column(String(100), nullable=False, index=True)  # 자연, 힐링, 카페, 액티비티, 문화/역사, 맛집, 실내 등
    
    # 위치 정보 (경로 최적화 및 거리 계산용)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # 상세 설명 (임베딩 텍스트 원본)
    description = Column(Text, nullable=False)
    
    # 여행 속성 메타데이터 (JSONB)
    # {
    #   "companion_types": ["커플", "혼자", "가족", "친구", "반려견"],
    #   "best_seasons": ["봄", "가을", "사계절"],
    #   "weather_suitability": ["맑음", "비오는날_실내", "흐림"],
    #   "tags": ["오션뷰", "감성카페", "산책로", "포토존", "조용한", "주차가능"],
    #   "estimated_stay_min": 90,
    #   "cost_level": "저렴" | "보통" | "고급",
    #   "phone": "033-xxx-xxxx"
    # }
    spot_metadata = Column("metadata", JSONB, default=dict, nullable=False)

    # 768차원 ko-sroberta 시맨틱 임베딩 벡터
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        # HNSW 코사인 유사도 인덱스
        Index(
            "idx_travel_spots_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # 한국어 키워드 검색을 위한 GIN Trigram 인덱스
        Index(
            "idx_travel_spots_name_trgm",
            name,
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "idx_travel_spots_desc_trgm",
            description,
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
    )

    def __repr__(self):
        return f"<TravelSpot id={self.id} name={self.name} region={self.region}>"
