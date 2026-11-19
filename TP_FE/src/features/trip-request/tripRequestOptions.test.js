import { REGION_GEO } from "../map/regionGeo";
import { COMPANIONS, REGIONS, THEMES, TRANSPORTS, toAreaCodes } from "./tripRequestOptions";

describe("tripRequestOptions", () => {
  it("지역 16개를 화면 표시 순서로 가진다", () => {
    expect(REGIONS.map((r) => r.label)).toEqual([
      "서울",
      "인천",
      "경기",
      "강원",
      "충북",
      "충남",
      "세종",
      "대전",
      "경북",
      "대구",
      "울산",
      "부산",
      "경남",
      "전북",
      "전남광주",
      "제주",
    ]);
    expect(new Set(REGIONS.map((r) => r.value)).size).toBe(16);
  });

  it("전남광주는 TourAPI 지역코드 전남(38)·광주(5)로 펼친다", () => {
    expect(toAreaCodes("38")).toEqual(["38", "5"]);
  });

  it("일반 지역은 value 하나, 목록에 없는 값은 그대로 보낸다", () => {
    expect(toAreaCodes("6")).toEqual(["6"]);
    expect(toAreaCodes("999")).toEqual(["999"]);
  });

  it("지역 버튼 목록과 지도 좌표(regionGeo)의 키가 같다", () => {
    expect(REGIONS.map((r) => r.value).sort()).toEqual(Object.keys(REGION_GEO).sort());
  });

  it("선택지 value 가 중복되지 않는다", () => {
    [COMPANIONS, TRANSPORTS, THEMES].forEach((options) => {
      expect(new Set(options.map((o) => o.value)).size).toBe(options.length);
    });
  });
});
