import '@testing-library/jest-dom';
import { TextDecoder, TextEncoder } from 'node:util';

// jsdom 에는 TextEncoder/TextDecoder 가 없어 react-router(v7) import 시 오류가 나므로 Node 내장 구현을 주입한다.
Object.assign(globalThis, { TextEncoder, TextDecoder });

// import.meta.env 는 Jest 에서 파싱되지 않으므로 env 모듈을 항상 mock 으로 대체한다.
// 값은 src/config/__mocks__/env.js 참고. 테스트별로 바꾸려면 해당 테스트에서 jest.mock 을 재정의한다.
jest.mock('./src/config/env');
