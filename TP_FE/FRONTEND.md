# TP Frontend (FRONTEND.md)

> AI 기반 국내 여행 일정 추천 서비스 **TP**의 프론트엔드 명세이자 작업 규칙.
> 팀원과 AI 코딩 도구(Claude Code 등)가 모두 이 문서를 기준으로 작업한다. `TP_FE/CLAUDE.md`는 이 문서를 불러오기만 한다.

- 위치: 모노레포 `Mini_Project_1/` 의 `TP_FE/`
- 담당: 전인찬 (지도·동선, 일정 화면, 공유)
- 전체 구조·협업 규칙은 [ROOT.md](../ROOT.md), 백엔드 API는 [BACKEND.md](../TP_BE/BACKEND.md)

---

## 1. 서비스 범위

- 국내 여행 전용, 지도는 카카오맵
- 웹 우선, 데스크톱 기준(최소 너비 1280px). 모바일 대응은 이후 작업
- 라이트 모드만 지원 (카카오맵이 다크모드를 지원하지 않아 제외)
- 로그인 없이 모든 기능 사용 가능. 로그인은 개발 마지막에 구현
- 사용자 입력은 자연어 대신 선택형으로 구성

## 2. 기술 스택

| 항목 | 사용 | 비고 |
| :--- | :--- | :--- |
| 빌드·언어 | Vite + React, **JavaScript** | TypeScript 아님 |
| 런타임 | Node 24, npm | `.node-version` 참고 |
| 라우팅·HTTP | react-router-dom, axios | |
| 스타일 | CSS Modules(`*.module.css`) + 디자인 토큰(CSS 변수) | UI 라이브러리·CSS 프레임워크 사용 안 함 |
| 린트·포맷 | ESLint + Prettier | |
| 테스트 | Jest + babel-jest + Testing Library (jsdom) | **Vitest 사용 금지** (팀 결정) |
| 지도 | Kakao Maps JavaScript SDK | |

**보류:** TypeScript, Zustand, TanStack Query는 도입하지 않는다. 일정 편집 화면(E-21~22) 착수 시 지도↔타임라인 상태 공유가 필요해지면 다시 판단한다.

## 3. 명령어

```bash
cd TP_FE
npm install
npm run dev           # http://localhost:5173, /api → http://localhost:8080 proxy
npm run build
npm run lint
npm run format        # prettier --write
npm run format:check
npm test
```

커밋 전 `npm run lint`, `npm test`, `npm run build` 모두 통과해야 한다.

## 4. 폴더 구조

```text
TP_FE/
├─ src/
│  ├─ pages/          # 라우트 단위 페이지. 페이지 전용 컴포넌트는 pages/{page}/components/
│  │  ├─ main/        # 메인페이지 (일정 생성 질문 흐름)
│  │  └─ itinerary/   # 일정 화면
│  ├─ components/     # 도메인 무관 재사용 UI만 (Button, Chip, layout/, icons/ …)
│  ├─ features/       # 도메인별 상태·규칙·API 호출
│  │  ├─ map/         # 지도. SDK 직접 호출은 map/mapProvider/ 안에서만
│  │  └─ trip-request/# 일정 생성 요청 (질문 상태, 요청 변환, API, mock)
│  ├─ api/client.js   # axios 클라이언트 (apiClient)
│  ├─ hooks/          # 도메인 무관 공통 훅
│  ├─ utils/          # 도메인 무관 순수 함수 (logger 등)
│  ├─ config/env.js   # 환경변수 접근 단일 지점
│  └─ styles/global.css
├─ test/              # Jest용 mock (styleMock.js, fileMock.js)
├─ jest.config.js, jest.setup.js, babel.config.cjs
├─ eslint.config.js, .prettierrc.json
└─ vite.config.js
```

- 새 도메인은 `features/{도메인}/` 에 만든다. 기능명세서 도메인 기준: `map`, `itinerary`, `sharing`, `auth`
- 파일명: 컴포넌트는 `PascalCase.jsx`, 훅은 `useXxx.js`, 그 외 `camelCase.js`. 테스트는 대상 파일 옆에 `*.test.js(x)`

## 5. 화면 구성

| 화면 | 경로 | 기능 ID | 상태 |
| :--- | :--- | :--- | :--- |
| 메인 (지도 탐색 + 질문 흐름) | `/` | — | 구현됨 (mock 응답) |
| 일정 편집 (지도 전체 + 플로팅 패널, B안) | `/itinerary/:id` | D-16~20, E-21~22 | 자리만 있음 |
| 한눈에 보기 (읽기 전용, C안) | 미정 | — | 예정 |
| 공유 (링크·이미지) | 미정 | F-26 | 예정 |

### 5.1 메인페이지 질문 흐름
1. 지역 선택 → 지도가 해당 지역으로 확대
2. 필수 질문: 날짜 → 동행 → 인원(혼자면 건너뜀) → 이동수단
3. 선택 질문(기본값 선택 상태): 취향 · 하루 방문 수 · 시작 시간
4. 일정 만들기 → 생성 중 화면 → `/itinerary/:id`

답한 내용은 칩으로 쌓이고 칩을 누르면 해당 질문으로 돌아간다. 생성 중에는 답을 바꿀 수 없다.

## 6. 디자인 토큰

`src/styles/global.css` 의 `:root` 변수만 사용한다. 색·모서리·그림자를 컴포넌트에 직접 쓰지 않는다.

- 주요 색: `--color-primary`(앰버 #F2B01E), `--color-secondary`(인디고 #3949AB)
- 글자·면: `--color-ink`, `--color-ink-soft`, `--color-surface`, `--color-bg`, `--color-line`
- 모서리: `--radius-sm` ~ `--radius-2xl` / 그림자: `--shadow-sm`, `--shadow-md`
- 폰트: Pretendard (`--font-sans`)

새 토큰이 필요하면 global.css 에 추가하고 이 목록을 갱신한다. 카카오맵 객체처럼 CSS 변수를 쓸 수 없는 곳은 같은 값을 `features/map` 안의 상수로 둔다.

## 7. 카카오맵 연동

- SDK(`window.kakao` 등) 직접 호출은 **`src/features/map/mapProvider/` 안에서만** 한다. 다른 곳은 mapProvider 가 노출하는 함수만 쓴다.
- SDK 로드는 `mapProvider/loadMapSdk.js` 에서 한다.
  - 주소는 `https://dapi.kakao.com/v2/maps/sdk.js?appkey=…&autoload=false`
  - 로드 Promise 를 캐싱해 여러 번 호출해도 스크립트를 한 번만 넣는다
  - 실패 시 오류를 던지고, 화면은 오류 상태를 보여준다
- 지도를 쓰는 컴포넌트는 언마운트 시 마커·오버레이·이벤트를 정리한다
- 동선 표시(예정): 순서 번호 마커는 `CustomOverlay`, 경로는 `Polyline`, 일자별 장소가 모두 보이도록 `LatLngBounds` 로 범위 조정

## 8. API 통신

- 모든 요청은 `src/api/client.js` 의 `apiClient` 를 사용한다
- 백엔드는 `ApiResponse<T>`(`success`, `code`, `message`, `data`, `timestamp`)로 감싸서 응답한다. `apiClient` 가 `data` 만 꺼내 반환하고, `success: false` 나 통신 오류는 `message` 를 담은 Error 로 바꾼다
- 응답 필드는 **camelCase 그대로** 쓴다. 이름 변환 레이어를 만들지 않는다
- 엔드포인트는 [BACKEND.md](../TP_BE/BACKEND.md) 를 따른다. 일정 생성은 `POST /api/v1/trips`
- `VITE_USE_MOCK=true` 이면 `features/*/…Api.mock.js` 의 mock 응답을 쓴다
- 일정 생성 요청 형태는 AI 담당과 협의 중인 초안이다. 확정 전에는 `features/trip-request/toTripRequest.js` 에서만 변환한다

## 9. 환경변수

`import.meta.env` 는 **`src/config/env.js` 에서만** 읽는다. (Jest 에서 `import.meta` 가 동작하지 않아 테스트는 `src/config/__mocks__/env.js` 로 대체되며 `jest.setup.js` 에서 전역 적용된다)

| 키 | 용도 | 로컬 값 |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | API 기본 주소 | 비워두면 `/api/v1` (Vite proxy 사용). 운영에서만 전체 주소 |
| `VITE_KAKAO_MAP_API_KEY` | 카카오맵 JavaScript 키 | 각자 발급 키 |
| `VITE_USE_MOCK` | mock 응답 사용 | `true` / `false` |

로컬에서 `VITE_API_BASE_URL` 에 `http://localhost:8080` 을 직접 넣으면 proxy 를 거치지 않아 CORS 오류가 난다.

## 10. 코드 스타일

- Prettier: 큰따옴표, 세미콜론, printWidth 100 (`.prettierrc.json`)
- 컴포넌트는 함수 선언, props 이벤트는 `onXxx`, 내부 핸들러는 `handleXxx`
- 지도 마커·목록 아이템처럼 자주 다시 그려지는 컴포넌트는 `React.memo`, 무거운 계산은 `useMemo`
- 로그: `console.log` 대신 `src/utils/logger.js` 를 쓴다
- 페이지와 지도 영역에는 Error Boundary 를 두어 오류 시 화면 전체가 비지 않게 한다

## 11. 테스트

- 위치: `src/**/*.test.{js,jsx}`
- 필수 대상: `features/` 의 상태·규칙·변환 함수, `api` 호출 훅, 공통 컴포넌트의 주요 동작
- 지도는 `features/map/mapProvider/__mocks__` 로 대체해 SDK 없이 테스트한다

## 12. Git

- 브랜치·PR 규칙은 [ROOT.md](../ROOT.md) 를 따른다
- 커밋은 Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`

### PR 확인 항목
- [ ] 지도 컴포넌트 언마운트 시 정리가 되는가
- [ ] API 오류·로딩 상태 처리가 빠지지 않았는가
- [ ] 디자인 토큰 대신 색·크기를 직접 쓴 곳이 없는가
- [ ] lint, test, build 통과

---

## 13. AI 코딩 도구 작업 규칙

다음은 반드시 지킨다.

- 위 폴더 구조와 이름 규칙을 따른다. 맞지 않는 구조가 필요하면 먼저 사용자에게 묻는다
- 카카오맵 SDK 직접 호출은 `features/map/mapProvider/` 밖에서 하지 않는다
- `import.meta.env` 는 `config/env.js` 밖에서 쓰지 않는다
- `.env`, `.env.local` 등 `.env*` 파일을 만들거나 고치지 않는다. 새 키가 필요하면 `.env.example` 에 이름만 추가하고 사용자에게 알린다
- 시크릿·API 키를 코드에 쓰지 않는다
- 패키지(dependencies/devDependencies)를 추가하기 전에 사용자에게 묻는다
- 다크모드(`prefers-color-scheme: dark`) 코드를 쓰지 않는다
- 사용자가 요청하기 전에는 커밋하지 않는다
- `TP_FE/` 밖(백엔드, AI, 배치, 루트 문서)은 사용자가 요청할 때만 수정한다
- 작업이 끝나면 lint, test, build 결과를 알린다
