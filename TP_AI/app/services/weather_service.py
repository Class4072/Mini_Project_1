from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.weather import WeatherForecast
from app.schemas.ai import DailyWeatherInput
from app.core.logger import app_logger


class WeatherService:
    """기상청 예보 DB(weather_forecasts) 조회 및 적재 서비스"""

    async def get_daily_weathers(
        self,
        db: AsyncSession,
        region_name: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyWeatherInput]:
        """DB에 주기적으로 적재된 기상청 예보 데이터에서 지정된 지역/기간의 날씨 조회"""
        try:
            stmt = (
                select(WeatherForecast)
                .where(
                    and_(
                        WeatherForecast.region.ilike(f"%{region_name}%"),
                        WeatherForecast.forecast_date >= start_date,
                        WeatherForecast.forecast_date <= end_date,
                    )
                )
                .order_by(WeatherForecast.forecast_date.asc())
            )
            res = await db.execute(stmt)
            rows = res.scalars().all()

            if not rows:
                return []

            date_map = {r.forecast_date: r for r in rows}
            total_days = max(1, (end_date - start_date).days + 1)
            results: List[DailyWeatherInput] = []

            for d_idx in range(total_days):
                curr_d = start_date + timedelta(days=d_idx)
                if curr_d in date_map:
                    row = date_map[curr_d]
                    results.append(
                        DailyWeatherInput(
                            date=curr_d,
                            condition=row.condition,
                            temp=row.temp_avg if row.temp_avg is not None else row.temp_max,
                            precipitationProbability=row.precipitation_probability,
                        )
                    )
                else:
                    # 해당 일자 데이터가 누락된 경우 None 반환하여 부분 Fallback 유도
                    return []

            app_logger.info(
                f"🌤️ [기상청 예보 DB 조회 성공] region={region_name}, period={start_date}~{end_date}, rows={len(results)}"
            )
            return results

        except Exception as e:
            app_logger.warning(f"기상청 예보 DB 조회 중 오류 발생 (Fallback 전환): {e}")
            return []


weather_service = WeatherService()

