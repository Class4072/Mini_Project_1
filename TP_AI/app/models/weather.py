import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Date,
    Float,
    Integer,
    DateTime,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class WeatherForecast(Base):
    """기상청 단기/중기 예보 API 배치 적재 및 여행 일정 연동용 일자별 기상 예보 모델"""
    __tablename__ = "weather_forecasts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 지역 정보 (e.g. '부산', '강원도', '서울', '제주' 등)
    region = Column(String(100), nullable=False, index=True)
    
    # 예보 일자 (YYYY-MM-DD)
    forecast_date = Column(Date, nullable=False, index=True)
    
    # 기상 상태 코드 (SUNNY: 맑음, RAIN: 비, CLOUDY: 흐림/구름많음, SNOW: 눈)
    condition = Column(String(50), nullable=False)
    
    # 기온 정보 (℃)
    temp_avg = Column(Float, nullable=True)  # 평균 기온
    temp_min = Column(Float, nullable=True)  # 최저 기온
    temp_max = Column(Float, nullable=True)  # 최고 기온
    
    # 강수 확률 (%)
    precipitation_probability = Column(Integer, default=0, nullable=False)
    
    # 기상 요약 및 특보 안내 (e.g. '오후 한때 비, 강풍 주의', '맑고 쾌적한 가을 날씨')
    weather_description = Column(Text, nullable=True)
    
    # 데이터 적재/갱신 시각 (기상청 배치 실행 시점)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        # 지역 + 예보 날짜 복합 유니크 제약 (동일 일자 중복 적재 방지 및 초고속 인덱스 스캔)
        UniqueConstraint("region", "forecast_date", name="uq_weather_region_date"),
        Index("idx_weather_region_date", "region", "forecast_date"),
    )

    def __repr__(self):
        return f"<WeatherForecast region={self.region} date={self.forecast_date} condition={self.condition} temp={self.temp_avg}℃>"

