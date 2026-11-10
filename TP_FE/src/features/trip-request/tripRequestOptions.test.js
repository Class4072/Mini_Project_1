import { COMPANIONS, REGIONS, THEMES, TRANSPORTS } from './tripRequestOptions';

describe('tripRequestOptions', () => {
  it('지역 17개를 화면 표시 순서로 가진다', () => {
    expect(REGIONS.map((r) => r.label)).toEqual([
      '서울',
      '인천',
      '경기',
      '강원',
      '충북',
      '충남',
      '세종',
      '대전',
      '경북',
      '대구',
      '울산',
      '부산',
      '경남',
      '전북',
      '전남',
      '광주',
      '제주',
    ]);
    expect(new Set(REGIONS.map((r) => r.value)).size).toBe(17);
  });

  it('선택지 value 가 중복되지 않는다', () => {
    [COMPANIONS, TRANSPORTS, THEMES].forEach((options) => {
      expect(new Set(options.map((o) => o.value)).size).toBe(options.length);
    });
  });
});
