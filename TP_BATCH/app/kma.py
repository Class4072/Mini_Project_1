"""기상청 단기예보 조회 클라이언트 (BT-010, BATCH.md 10.2).

공공데이터포털(apis.data.go.kr)과 기상청 API 허브(apihub.kma.go.kr)는 같은 응답을 준다.
키를 넘기는 파라미터 이름만 다르다: 포털은 serviceKey, 허브는 authKey.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from urllib.parse import quote, unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.quota import QuotaExhausted
from app.tourapi.client import (
    LIMIT_EXCEEDED_CODE,
    LIMIT_EXCEEDED_TEXT,
    _extract_items,
    _to_int,
    service_name,
)

log = logging.getLogger(__name__)

Item = Dict[str, Any]

OK_CODE = "00"
NO_DATA_CODE = "03"

# 단기예보 발표 시각. 발표 후 10분쯤 지나야 조회된다.
BASE_HOURS = (2, 5, 8, 11, 14, 17, 20, 23)
PUBLISH_DELAY = timedelta(minutes=10)

# 발표 한 번의 예보는 지점당 1,000건 안팎이다. 모자라면 다음 페이지를 읽는다.
NUM_OF_ROWS = 1000
MAX_PAGES = 5


class KmaApiError(RuntimeError):
    """기상청 API가 resultCode != 00으로 응답한 경우."""

    def __init__(self, result_code: str, result_msg: str):
        super().__init__("기상청 API 오류 [{0}]: {1}".format(result_code, result_msg))
        self.result_code = result_code


def latest_base_time(now: datetime) -> datetime:
    """now(한국 시간) 기준으로 조회할 수 있는 가장 최근 발표 시각."""
    t = now - PUBLISH_DELAY
    for hour in reversed(BASE_HOURS):
        if t.hour >= hour:
            return t.replace(hour=hour, minute=0, second=0, microsecond=0)
    yesterday = t - timedelta(days=1)
    return yesterday.replace(hour=BASE_HOURS[-1], minute=0, second=0, microsecond=0)


def previous_base_time(base: datetime) -> datetime:
    return base - timedelta(hours=3)


def is_hub(base_url: str) -> bool:
    return "apihub.kma.go.kr" in base_url


class KmaClient:
    def __init__(self, base_url: str, key: str, timeout_sec: int = 20, quota=None):
        """
        :param quota: app.quota.DailyQuota. 주어지면 호출마다 일일 카운트를 올린다.
        """
        if not key:
            raise RuntimeError(
                "기상청 API 키가 없습니다. 공공데이터포털 키는 KMA_API_KEY(비우면 TOUR_API_SERVICE_KEY), "
                "기상청 API 허브 키는 KMA_API_AUTH_KEY에 넣으세요 (.env.example 참고)."
            )
        self.base_url = base_url.rstrip("/")
        # 포털의 인코딩 키(%2B, %3D 포함)를 넣어도 되게 푼다. 요청할 때 다시 인코딩된다.
        self.key = unquote(key) if "%" in key else key
        self.key_param = "authKey" if is_hub(self.base_url) else "serviceKey"
        self.timeout_sec = timeout_sec
        self.quota = quota
        self.service = service_name(self.base_url)

        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def close(self) -> None:
        self.session.close()

    def fetch_forecast(self, base: datetime, nx: int, ny: int) -> List[Item]:
        """한 격자의 단기예보 전체 (발표 시각 base 기준)."""
        collected: List[Item] = []
        for page_no in range(1, MAX_PAGES + 1):
            body = self._request(
                {
                    "base_date": base.strftime("%Y%m%d"),
                    "base_time": base.strftime("%H00"),
                    "nx": str(nx),
                    "ny": str(ny),
                    "pageNo": str(page_no),
                    "numOfRows": str(NUM_OF_ROWS),
                    "dataType": "JSON",
                }
            )
            items = _extract_items(body)
            collected.extend(items)
            if not items or len(collected) >= _to_int(body.get("totalCount"), 0):
                break
        return collected

    def _request(self, params: Dict[str, str]) -> Dict[str, Any]:
        query = {self.key_param: self.key}
        query.update(params)

        if self.quota is not None:
            self.quota.acquire(self.service)

        url = "{0}/getVilageFcst".format(self.base_url)
        try:
            response = self.session.get(url, params=query, timeout=self.timeout_sec)
        except requests.RequestException as exc:
            if "429" in str(exc):
                self._on_server_limit("HTTP 429")
            # 예외 문구에 요청 URL(키 포함)이 들어 있어 키를 가리고, 원래 예외도 잇지 않는다
            raise RuntimeError("기상청 API 요청 실패: {0}".format(self._mask(str(exc)))) from None

        head = response.text[:2000]
        if LIMIT_EXCEEDED_TEXT in head:
            self._on_server_limit(LIMIT_EXCEEDED_TEXT)
        if not (200 <= response.status_code < 300):
            raise RuntimeError(
                "기상청 API HTTP {0} 응답: {1}".format(response.status_code, self._mask(head[:300]))
            )
        try:
            root = response.json()
        except ValueError:
            # 키가 틀리거나 활용신청을 안 했으면 JSON 대신 XML 오류 문서가 온다
            raise RuntimeError(
                "기상청 API 응답을 JSON으로 읽을 수 없습니다 (키·활용신청 확인): {0}".format(
                    self._mask(head[:300])
                )
            ) from None

        response_part = root.get("response") or {}
        header = response_part.get("header") or {}
        result_code = str(header.get("resultCode", OK_CODE))
        if result_code != OK_CODE:
            result_msg = str(header.get("resultMsg", "unknown"))
            if result_code == LIMIT_EXCEEDED_CODE:
                self._on_server_limit(result_msg)
            raise KmaApiError(result_code, result_msg)
        return response_part.get("body") or {}

    def _mask(self, text: str) -> str:
        for secret in {self.key, quote(self.key, safe="")}:
            if secret:
                text = text.replace(secret, "***")
        return text

    def _on_server_limit(self, detail: str) -> None:
        if self.quota is not None:
            self.quota.mark_exhausted(self.service)
        raise QuotaExhausted(self.service, "서버 응답: {0}".format(detail))
