import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { createMap, loadMapSdk } from '../../features/map/mapProvider';
import { generateItinerary } from '../../features/trip-request/tripRequestApi';
import ItineraryPage from '../itinerary/ItineraryPage';
import MainPage from './MainPage';

jest.mock('../../features/map/mapProvider');
jest.mock('../../features/trip-request/tripRequestApi');

// 기본은 SDK 로딩·일정 생성이 끝나지 않은 상태로 둔다. (끝난 뒤 동작은 해당 테스트에서 따로 검사)
beforeEach(() => {
  jest.clearAllMocks();
  loadMapSdk.mockReturnValue(new Promise(() => {}));
  generateItinerary.mockReturnValue(new Promise(() => {}));
});

function renderMainPage() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/itinerary/:itineraryId" element={<ItineraryPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const mapArea = () => screen.getByRole('region', { name: '지도' });

const day = (label) => screen.getByRole('button', { name: label });
const nextButton = () => screen.getByRole('button', { name: '다음' });

function goToDateStep() {
  renderMainPage();
  fireEvent.click(screen.getByRole('button', { name: '부산' }));
}

function showNovember() {
  fireEvent.click(screen.getByRole('button', { name: '다음 달' }));
}

describe('MainPage', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-10-20T10:00:00+09:00'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('첫 화면에 17개 지역 버튼이 보인다', () => {
    renderMainPage();
    expect(screen.getByRole('heading', { name: /어디로 떠날까요\?/ })).toBeInTheDocument();
    const grid = screen.getByRole('heading', { name: '지역 고르기' }).nextElementSibling;
    expect(within(grid).getAllByRole('button')).toHaveLength(17);
    expect(within(mapArea()).getByText('지도를 불러오는 중이에요')).toBeInTheDocument();
  });

  it('지역을 누르면 날짜 질문, 지역 칩, 진행 표시가 보인다', () => {
    goToDateStep();
    expect(screen.getByRole('heading', { name: '언제 가나요?' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '부산' })).toBeInTheDocument();
    expect(screen.getByText('1 / 4')).toBeInTheDocument();
    expect(within(mapArea()).getByText('부산')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '이전' })).not.toBeInTheDocument();
  });

  it('처음에는 오늘이 있는 달을 보여주고 오늘 이전 날짜는 비활성이다', () => {
    goToDateStep();
    expect(screen.getByText('2026년 10월')).toBeInTheDocument();
    expect(day('2026년 10월 19일 월요일')).toBeDisabled();
    expect(day('2026년 10월 20일 화요일')).toBeEnabled();
    expect(screen.getByRole('button', { name: '이전 달' })).toBeDisabled();
  });

  it('11월 1일 → 11월 3일을 누르면 2박 3일이 보이고 다음 버튼이 활성화된다', () => {
    goToDateStep();
    showNovember();
    expect(nextButton()).toBeDisabled();

    fireEvent.click(day('2026년 11월 1일 일요일'));
    fireEvent.click(day('2026년 11월 3일 화요일'));

    expect(screen.getByText('2박 3일')).toBeInTheDocument();
    expect(screen.getByText('11월 1일 (일)')).toBeInTheDocument();
    expect(screen.getByText('11월 3일 (화)')).toBeInTheDocument();
    expect(day('2026년 11월 1일 일요일')).toHaveAttribute('aria-pressed', 'true');
    expect(day('2026년 11월 3일 화요일')).toHaveAttribute('aria-pressed', 'true');
    expect(day('2026년 11월 2일 월요일')).toHaveAttribute('aria-pressed', 'false');
    expect(nextButton()).toBeEnabled();
  });

  it('같은 날을 두 번 누르면 당일치기', () => {
    goToDateStep();
    showNovember();
    fireEvent.click(day('2026년 11월 1일 일요일'));
    fireEvent.click(day('2026년 11월 1일 일요일'));
    expect(screen.getByText('당일치기')).toBeInTheDocument();
    expect(nextButton()).toBeEnabled();
  });

  it('출발일만 고른 상태에서는 다음 버튼이 비활성이다', () => {
    goToDateStep();
    showNovember();
    fireEvent.click(day('2026년 11월 1일 일요일'));
    expect(screen.getByText('11월 1일 (일)')).toBeInTheDocument();
    expect(screen.getByText('선택해주세요')).toBeInTheDocument();
    expect(nextButton()).toBeDisabled();
  });

  it('다음으로 넘어가면 날짜 칩이 생기고, 누르면 날짜 단계로 돌아온다', () => {
    goToDateStep();
    showNovember();
    fireEvent.click(day('2026년 11월 1일 일요일'));
    fireEvent.click(day('2026년 11월 3일 화요일'));
    fireEvent.click(nextButton());

    expect(screen.getByText('2 / 4')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '누구와 가나요?' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '11/1~11/3 · 2박 3일' }));
    expect(screen.getByRole('heading', { name: '언제 가나요?' })).toBeInTheDocument();
    // 출발일이 있으면 그 달을 연다
    expect(screen.getByText('2026년 11월')).toBeInTheDocument();
  });
});

describe('MainPage 나머지 질문', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-10-20T10:00:00+09:00'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const press = (name) => fireEvent.click(screen.getByRole('button', { name }));
  const heading = (name) => screen.getByRole('heading', { name });

  function goToCompanionStep() {
    renderMainPage();
    press('부산');
    showNovember();
    press('2026년 11월 1일 일요일');
    press('2026년 11월 3일 화요일');
    press('다음');
  }

  function goToOptionalStep() {
    goToCompanionStep();
    press('친구');
    press('다음');
    press('3명');
    press('다음');
    press(/^대중교통/);
    press('다음');
  }

  it('동행을 고르면 다음 버튼이 활성화되고 인원 질문으로 넘어간다', () => {
    goToCompanionStep();
    expect(heading('누구와 가나요?')).toBeInTheDocument();
    ['혼자', '연인·부부', '친구', '아이와 함께', '부모님과 함께', '단체'].forEach((name) => {
      expect(screen.getByRole('button', { name })).toHaveAttribute('aria-pressed', 'false');
    });
    expect(nextButton()).toBeDisabled();

    press('친구');
    expect(screen.getByRole('button', { name: '친구' })).toHaveAttribute('aria-pressed', 'true');
    press('다음');

    expect(heading('몇 명이 가나요?')).toBeInTheDocument();
    expect(screen.getByText('3 / 4')).toBeInTheDocument();
    // 인원 단계에서는 동행 칩에 인원을 붙이지 않는다
    expect(screen.getByRole('button', { name: '친구' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '2명' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('혼자를 고르면 인원 질문을 건너뛴다', () => {
    goToCompanionStep();
    press('혼자');
    press('다음');
    expect(heading('무엇으로 이동하나요?')).toBeInTheDocument();
    expect(screen.getByText('3 / 3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '혼자' })).toBeInTheDocument();
  });

  it('6명 이상을 고르면 조절 박스로 인원을 맞춘다', () => {
    goToCompanionStep();
    press('친구');
    press('다음');

    expect(screen.getByRole('button', { name: '인원 줄이기' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '인원 늘리기' })).toBeDisabled();

    press('6명 이상');
    expect(screen.getByText('6명')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '인원 줄이기' })).toBeDisabled();

    press('인원 늘리기');
    press('인원 늘리기');
    expect(screen.getByText('8명')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '6명 이상' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );

    // 이미 6명 이상이면 다시 눌러도 인원 유지
    press('6명 이상');
    expect(screen.getByText('8명')).toBeInTheDocument();

    press('인원 줄이기');
    expect(screen.getByText('7명')).toBeInTheDocument();
  });

  it('이동수단을 고르면 선택 질문으로 넘어가고 답한 칩이 모두 보인다', () => {
    goToOptionalStep();
    expect(heading('원하는 여행 스타일이 있나요?')).toBeInTheDocument();
    expect(screen.getByText('필수 완료')).toBeInTheDocument();
    ['부산', '11/1~11/3 · 2박 3일', '친구 3명', '대중교통'].forEach((name) => {
      expect(screen.getByRole('button', { name })).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: '이전' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '다음' })).not.toBeInTheDocument();
  });

  it('이동수단 카드에 설명 문구가 보인다', () => {
    goToCompanionStep();
    press('혼자');
    press('다음');
    expect(screen.getByText('역·정류장에서 가까운 곳 위주로 짜요.')).toBeInTheDocument();
    expect(nextButton()).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: /^자동차/ }));
    expect(nextButton()).toBeEnabled();
  });

  it('취향은 골고루가 기본이고 3개까지 고를 수 있다', () => {
    goToOptionalStep();
    const theme = (name) => screen.getByRole('button', { name });
    expect(theme('골고루')).toHaveAttribute('aria-pressed', 'true');

    press('자연·풍경');
    press('맛집');
    press('카페');
    expect(theme('골고루')).toHaveAttribute('aria-pressed', 'false');
    expect(theme('쇼핑')).toHaveAttribute('aria-disabled', 'true');
    expect(theme('맛집')).not.toHaveAttribute('aria-disabled');

    press('쇼핑');
    expect(theme('쇼핑')).toHaveAttribute('aria-pressed', 'false');

    press('골고루');
    expect(theme('골고루')).toHaveAttribute('aria-pressed', 'true');
    expect(theme('쇼핑')).not.toHaveAttribute('aria-disabled');
  });

  it('하루 장소 수와 시작 시간 기본값이 선택되어 있고 바꿀 수 있다', () => {
    goToOptionalStep();
    expect(screen.getByRole('button', { name: '4~5곳 적당히' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: '10:00 보통' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );

    press('11:00 느긋하게 · 퇴실 후');
    expect(screen.getByRole('button', { name: '11:00 느긋하게 · 퇴실 후' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: '10:00 보통' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  describe('일정 만들기', () => {
    const submitButton = () => screen.getByRole('button', { name: /일정 만들기|만드는 중…/ });

    it('누르면 요청 본문으로 일정 생성을 호출하고, 제출 중에는 버튼과 답을 막는다', () => {
      goToOptionalStep();
      press('맛집');
      press('일정 만들기');

      expect(generateItinerary).toHaveBeenCalledWith({
        regionCodes: ['6'],
        startDate: '2026-11-01',
        endDate: '2026-11-03',
        companionType: 'FRIENDS',
        travelerCount: 3,
        transport: 'PUBLIC_TRANSIT',
        themes: ['FOOD'],
        placesPerDay: 'NORMAL',
        startTime: 'NORMAL',
      });
      expect(submitButton()).toHaveTextContent('만드는 중…');
      expect(submitButton()).toBeDisabled();
      expect(submitButton()).toHaveAttribute('aria-busy', 'true');
      expect(screen.getByText('잠시만 기다려 주세요. 일정을 만들고 있어요.')).toBeInTheDocument();

      fireEvent.click(submitButton());
      expect(generateItinerary).toHaveBeenCalledTimes(1);

      // 칩·선택지는 누를 수 없다
      ['부산', '11/1~11/3 · 2박 3일', '친구 3명', '대중교통', '골고루', '카페'].forEach((name) => {
        expect(screen.getByRole('button', { name })).toBeDisabled();
      });
      // disabled fieldset 안의 버튼이라 브라우저에서는 클릭되지 않는다.
      // (jsdom 의 fireEvent 는 fieldset 비활성을 무시하고 클릭을 보내므로 disabled 여부만 검사)
      expect(screen.getByRole('button', { name: '10:00 보통' })).toBeDisabled();
    });

    it('성공하면 일정 화면으로 이동하고, 처음으로를 누르면 첫 화면으로 돌아간다', async () => {
      generateItinerary.mockResolvedValue({ itineraryId: 'mock-1' });
      goToOptionalStep();
      press('일정 만들기');

      expect(
        await screen.findByRole('heading', { name: '일정 화면은 준비 중이에요' }),
      ).toBeInTheDocument();
      expect(screen.getByText('일정 ID: mock-1')).toBeInTheDocument();

      press('처음으로');
      expect(heading(/어디로 떠날까요\?/)).toBeInTheDocument();
    });

    it('실패하면 오류 문구를 보여주고, 다시 누르면 재호출한다', async () => {
      generateItinerary.mockRejectedValueOnce(new Error('server error'));
      goToOptionalStep();
      press('일정 만들기');

      expect(await screen.findByRole('alert')).toHaveTextContent(
        '일정을 만들지 못했어요. 잠시 후 다시 시도해주세요.',
      );
      expect(submitButton()).toHaveTextContent('일정 만들기');
      expect(submitButton()).toBeEnabled();
      expect(screen.getByRole('button', { name: '카페' })).toBeEnabled();

      press('일정 만들기');
      expect(generateItinerary).toHaveBeenCalledTimes(2);
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('실패한 뒤 답을 바꾸면 오류 문구가 사라진다', async () => {
      generateItinerary.mockRejectedValueOnce(new Error('server error'));
      goToOptionalStep();
      press('일정 만들기');
      await screen.findByRole('alert');

      press('카페');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('타임아웃이면 타임아웃 문구를 보여준다', async () => {
      generateItinerary.mockRejectedValueOnce(
        Object.assign(new Error('timeout of 120000ms exceeded'), { code: 'ECONNABORTED' }),
      );
      goToOptionalStep();
      press('일정 만들기');

      expect(await screen.findByRole('alert')).toHaveTextContent(
        '일정 만들기가 오래 걸려 멈췄어요. 잠시 후 다시 시도해주세요.',
      );
    });
  });

  describe('지역 바꾸기 팝업', () => {
    const regionChip = () => screen.getByRole('button', { name: '부산', expanded: false });

    it('지역 칩을 누르면 팝업이 열리고, 다른 지역을 고르면 단계와 답을 유지한 채 닫힌다', () => {
      goToCompanionStep();
      press('친구');
      fireEvent.click(regionChip());

      const dialog = screen.getByRole('dialog', { name: '지역 바꾸기' });
      expect(screen.getByRole('button', { name: '부산', expanded: true })).toHaveAttribute(
        'aria-haspopup',
        'dialog',
      );
      expect(within(dialog).getAllByRole('button', { pressed: true })).toHaveLength(1);
      expect(within(dialog).getByRole('button', { name: '부산' })).toHaveFocus();

      fireEvent.click(within(dialog).getByRole('button', { name: '제주' }));

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: '제주', expanded: false })).toHaveFocus();
      expect(within(mapArea()).getByText('제주')).toBeInTheDocument();
      expect(heading('누구와 가나요?')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '친구' })).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByRole('button', { name: '11/1~11/3 · 2박 3일' })).toBeInTheDocument();
    });

    it('닫기 버튼, Esc, 바깥 클릭으로 닫힌다', () => {
      goToCompanionStep();

      fireEvent.click(regionChip());
      press('닫기');
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

      fireEvent.click(regionChip());
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(regionChip()).toHaveFocus();

      fireEvent.click(regionChip());
      fireEvent.mouseDown(screen.getByRole('heading', { name: '누구와 가나요?' }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('열린 상태에서 지역 칩을 다시 누르면 닫힌다', () => {
      goToCompanionStep();
      fireEvent.click(regionChip());
      const chip = screen.getByRole('button', { name: '부산', expanded: true });
      fireEvent.mouseDown(chip);
      fireEvent.click(chip);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });
});

describe('MainPage 지도', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-10-20T10:00:00+09:00'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('지도 라벨로 지역을 고르면 왼쪽 목록과 같이 바로 날짜 질문으로 넘어간다', async () => {
    loadMapSdk.mockResolvedValue();
    renderMainPage();

    const handle = () => createMap.mock.results[0].value;
    await waitFor(() => expect(handle().setRegionLabels).toHaveBeenCalled());
    const { onClick } = handle().setRegionLabels.mock.calls.at(-1)[1];
    act(() => onClick('6'));

    expect(screen.getByRole('heading', { name: '언제 가나요?' })).toBeInTheDocument();
    expect(within(mapArea()).getByText('부산')).toBeInTheDocument();
    expect(handle().focus).toHaveBeenLastCalledWith({ lat: 35.1798, lng: 129.075 }, 9);
    expect(handle().setRegionLabels.mock.calls.at(-1)[0]).toContainEqual(
      expect.objectContaining({ code: '6', state: 'selected', lat: 35.1, lng: 129.1 }),
    );
  });

  it('지도를 불러오지 못해도 왼쪽 목록으로 질문을 이어갈 수 있다', async () => {
    loadMapSdk.mockRejectedValue(new Error('load failed'));
    renderMainPage();

    expect(
      await screen.findByText('지도를 불러오지 못했어요. 왼쪽 목록에서 지역을 골라주세요.'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '부산' }));
    expect(screen.getByRole('heading', { name: '언제 가나요?' })).toBeInTheDocument();
  });
});
