import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.weather import WeatherForecast
from app.schemas.ai import AIScheduleRequest, DailyWeatherInput, AIScheduleResponse
from app.services.weather_service import weather_service
from app.services.ai_schedule_service import ai_schedule_service


@pytest.mark.asyncio
async def test_weather_service_db_query_success():
    """DB에 적재된 기상청 예보가 정상적으로 DailyWeatherInput 리스트로 매핑되는지 검증"""
    mock_db = AsyncMock()
    
    forecast_day1 = WeatherForecast(
        region="부산광역시",
        forecast_date=date(2026, 11, 1),
        condition="RAIN",
        temp_avg=18.5,
        temp_max=21.0,
        temp_min=15.0,
        precipitation_probability=80,
    )
    forecast_day2 = WeatherForecast(
        region="부산광역시",
        forecast_date=date(2026, 11, 2),
        condition="SUNNY",
        temp_avg=20.0,
        temp_max=22.0,
        temp_min=16.0,
        precipitation_probability=10,
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [forecast_day1, forecast_day2]
    mock_db.execute.return_value = mock_res

    results = await weather_service.get_daily_weathers(
        db=mock_db,
        region_name="부산",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 2),
    )

    assert len(results) == 2
    assert results[0].date == date(2026, 11, 1)
    assert results[0].condition == "RAIN"
    assert results[0].temp == 18.5
    assert results[0].precipitationProbability == 80

    assert results[1].date == date(2026, 11, 2)
    assert results[1].condition == "SUNNY"
    assert results[1].temp == 20.0
    assert results[1].precipitationProbability == 10


@pytest.mark.asyncio
async def test_weather_service_missing_date_returns_empty():
    """일부 날짜의 예보가 누락된 경우 Fallback을 유도하기 위해 빈 리스트를 반환하는지 검증"""
    mock_db = AsyncMock()
    
    # 2일 여행인데 1일차 데이터만 있는 경우
    forecast_day1 = WeatherForecast(
        region="부산광역시",
        forecast_date=date(2026, 11, 1),
        condition="SUNNY",
        temp_avg=19.0,
        precipitation_probability=0,
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [forecast_day1]
    mock_db.execute.return_value = mock_res

    results = await weather_service.get_daily_weathers(
        db=mock_db,
        region_name="부산",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 2),
    )

    assert results == []


@pytest.mark.asyncio
async def test_weather_service_db_exception_graceful():
    """DB 조회 중 에러 발생 시 크래시 없이 빈 리스트(Fallback 유도)를 반환하는지 검증"""
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("DB Connection Timeout")

    results = await weather_service.get_daily_weathers(
        db=mock_db,
        region_name="부산",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 2),
    )

    assert results == []


@pytest.mark.asyncio
async def test_ai_schedule_weather_db_priority_and_fallback():
    """일정 생성 시 기상청 예보 DB 1순위 조회 및 DB 미적재 시 2순위 Fallback 전환 검증"""
    req = AIScheduleRequest(
        regionCodes=["6"],  # 부산
        startDate="2026-11-01",
        endDate="2026-11-01",
        themes=["NATURE"],
        dailyWeathers=None,  # 클라이언트 미입력 상태
    )

    mock_db = AsyncMock()
    # TravelSpot 검색 Mock
    from app.models.travel import TravelSpot
    mock_spot = TravelSpot(
        id=1,
        name="부산 아쿠아리움",
        region="부산광역시",
        category="실내 전시",
        latitude=35.16,
        longitude=129.16,
        spot_metadata={"is_indoor": True, "weather_suitability": ["비오는날_실내"]},
    )
    mock_search_res = MagicMock()
    mock_search_res.all.return_value = [(mock_spot, 0.85)]
    mock_db.execute.return_value = mock_search_res

    # 1. DB에 예보가 존재하는 경우 (1순위 DB 날씨 적용)
    db_forecast = [
        DailyWeatherInput(
            date=date(2026, 11, 1),
            condition="RAIN",
            temp=17.0,
            precipitationProbability=85,
        )
    ]

    mock_response = AIScheduleResponse(
        tripName="비 오는 날의 부산 실내 힐링",
        weatherSummary="비",
        dailySchedules=[],
    )

    with patch.object(weather_service, "get_daily_weathers", AsyncMock(return_value=db_forecast)) as mock_ws, \
         patch("app.core.llm_client.llm_client.generate_schedule_with_retry", AsyncMock(return_value=mock_response)) as mock_llm, \
         patch("app.core.embedding.embedding_service.embed_text_async", AsyncMock(return_value=[0.1] * 1536)):

        res = await ai_schedule_service.generate_schedule(mock_db, req)

        # 1순위 DB 조회가 호출되었는지 확인
        mock_ws.assert_called_once()
        # req.dailyWeathers에 DB 예보가 주입되었는지 확인
        assert req.dailyWeathers is not None
        assert req.dailyWeathers[0].condition == "RAIN"
        assert res.tripName == "비 오는 날의 부산 실내 힐링"

    # 2. DB에 예보가 없는 경우 (2순위 평년 계절 Fallback 적용)
    req2 = AIScheduleRequest(
        regionCodes=["6"],
        startDate="2026-11-01",
        endDate="2026-11-01",
        themes=["NATURE"],
        dailyWeathers=None,
    )

    with patch.object(weather_service, "get_daily_weathers", AsyncMock(return_value=[])) as mock_ws_empty, \
         patch("app.core.llm_client.llm_client.generate_schedule_with_retry", AsyncMock(return_value=mock_response)), \
         patch("app.core.embedding.embedding_service.embed_text_async", AsyncMock(return_value=[0.1] * 1536)):

        res2 = await ai_schedule_service.generate_schedule(mock_db, req2)

        mock_ws_empty.assert_called_once()
        # Fallback으로 생성된 날씨가 주입되었는지 확인
        assert req2.dailyWeathers is not None
        assert len(req2.dailyWeathers) == 1
        assert req2.dailyWeathers[0].date == date(2026, 11, 1)
        assert req2.dailyWeathers[0].condition in ["SUNNY", "RAIN"]
