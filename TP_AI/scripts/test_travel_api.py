import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app


def print_section(title: str):
    print(f"\n{'='*25} {title} {'='*25}")


def test_travel_api():
    with TestClient(app) as client:
        # 1. Health check
        print_section("1. Health Check (/health)")
        res = client.get("/health")
        print(f"Status Code: {res.status_code}")
        print(json.dumps(res.json(), indent=2, ensure_ascii=False))

        # 2. AI Travel Recommendation (Date, Person Count, Region)
        print_section("2. AI Travel Recommendation (POST /api/v1/travel/recommend)")
        recommend_payload = {
            "region": "강릉",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "person_count": 2,
            "theme_or_keyword": "바다 전망과 감성 카페 투어",
            "spots_per_day": 2,
        }
        res = client.post("/api/v1/travel/recommend", json=recommend_payload)
        print(f"Status Code: {res.status_code}")
        data = res.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # 3. Simple input test (Only region, start_date, person_count without extra keywords)
        print_section("3. Minimal Input Recommendation (Region + Dates + Person Count)")
        minimal_payload = {
            "region": "제주",
            "start_date": "2026-07-20",
            "end_date": "2026-07-21",
            "person_count": 4,
        }
        res_min = client.post("/api/v1/travel/recommend", json=minimal_payload)
        print(f"Status Code: {res_min.status_code}")
        data_min = res_min.json()
        print(f"Destination: {data_min['destination_summary']['requested_region']}")
        print(f"Companion Group: {data_min['destination_summary']['companion_group']}")
        print(f"Weather: {data_min['weather_summary']['expected_weather']} ({data_min['weather_summary']['expected_temperature']})")
        print(f"Total Days: {data_min['total_days']}, Spots: {data_min['total_spots_count']}")

        print("\n=== ALL TRAVEL AI TESTS COMPLETED SUCCESSFULLY! ===")


if __name__ == "__main__":
    test_travel_api()
