"""기상청 단기예보를 하루 한 줄 날씨로 합친다 (BT-010).

규칙 (DATABASE.md 팀 합의 6번, BATCH.md 5.2):
- 날씨: 09~21시 예보 중 가장 나쁜 것. SNOW > RAIN > CLOUDY > SUNNY
  - PTY 1(비)·2(비/눈)·4(소나기) → RAIN, 3(눈) → SNOW
  - PTY 0(강수 없음)이면 SKY 1(맑음) → SUNNY, 3(구름많음)·4(흐림) → CLOUDY
- 기온: 그날 최고기온(TMX). 없으면 09~21시 기온(TMP) 중 최댓값
- 강수확률: 09~21시 강수확률(POP) 중 최댓값

DB나 네트워크를 쓰지 않는 순수 함수만 둔다 (테스트하기 쉽게).
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

DAY_START_HOUR = 9
DAY_END_HOUR = 21

SEVERITY = {"SUNNY": 0, "CLOUDY": 1, "RAIN": 2, "SNOW": 3}
# 초단기예보 코드(5 빗방울, 6 빗방울눈날림, 7 눈날림)가 섞여 들어와도 처리한다
PTY_CONDITION = {1: "RAIN", 2: "RAIN", 4: "RAIN", 5: "RAIN", 6: "RAIN", 3: "SNOW", 7: "SNOW"}
SKY_CONDITION = {1: "SUNNY", 3: "CLOUDY", 4: "CLOUDY"}

HOURLY_CATEGORIES = ("SKY", "PTY", "POP", "TMP")


@dataclass(frozen=True)
class DailyWeather:
    date: date
    condition: str  # WeatherCondition: SUNNY / CLOUDY / RAIN / SNOW
    temperature: Optional[float]
    precipitation_prob: Optional[int]


def hour_condition(pty: Optional[int], sky: Optional[int]) -> Optional[str]:
    """한 시각의 PTY·SKY를 날씨 코드로 바꾼다. 판단할 값이 없으면 None."""
    if pty in PTY_CONDITION:
        return PTY_CONDITION[pty]
    if sky is None:
        return None
    return SKY_CONDITION.get(sky)


def aggregate_daily(items: Iterable[Dict[str, Any]], today: date) -> List[DailyWeather]:
    """getVilageFcst 응답 item 목록을 날짜별 한 줄로 합친다.

    - 지난 날짜는 버린다.
    - 오늘은 이미 지난 시각의 예보가 없으므로 남은 시간만으로 합친다.
    - 내일 이후는 오전(12시 이전)과 저녁(18시 이후) 예보가 모두 있어야 저장한다.
      예보 기간 마지막 날처럼 앞뒤가 잘린 날을 하루 날씨로 오해하지 않기 위해서다.
    """
    hourly: Dict[date, Dict[int, Dict[str, float]]] = {}
    daily_max: Dict[date, float] = {}

    for item in items:
        forecast_date = _parse_date(item.get("fcstDate"))
        hour = _parse_hour(item.get("fcstTime"))
        value = _number(item.get("fcstValue"))
        if forecast_date is None or hour is None or value is None:
            continue
        category = item.get("category")
        if category == "TMX":
            daily_max[forecast_date] = value
        elif category in HOURLY_CATEGORIES and DAY_START_HOUR <= hour <= DAY_END_HOUR:
            hourly.setdefault(forecast_date, {}).setdefault(hour, {})[category] = value

    result: List[DailyWeather] = []
    for forecast_date in sorted(hourly):
        by_hour = hourly[forecast_date]
        if forecast_date < today:
            continue
        if forecast_date > today and not (min(by_hour) <= 12 and max(by_hour) >= 18):
            continue

        conditions = [
            c
            for c in (hour_condition(_int(v.get("PTY")), _int(v.get("SKY"))) for v in by_hour.values())
            if c is not None
        ]
        if not conditions:
            continue
        temps = [v["TMP"] for v in by_hour.values() if "TMP" in v]
        pops = [int(v["POP"]) for v in by_hour.values() if "POP" in v and 0 <= v["POP"] <= 100]

        result.append(
            DailyWeather(
                date=forecast_date,
                condition=max(conditions, key=SEVERITY.__getitem__),
                temperature=daily_max.get(forecast_date, max(temps) if temps else None),
                precipitation_prob=max(pops) if pops else None,
            )
        )
    return result


def _parse_date(value: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(value).strip(), "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def _parse_hour(value: Any) -> Optional[int]:
    text = str(value or "").strip()
    if len(text) != 4 or not text.isdigit():
        return None
    return int(text[:2])


def _number(value: Any) -> Optional[float]:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    # 기상청은 값이 없을 때 +900 이상이나 -900 이하를 준다
    if number >= 900 or number <= -900:
        return None
    return number


def _int(value: Optional[float]) -> Optional[int]:
    return None if value is None else int(value)
