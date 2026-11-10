import { env } from "../config/env";

// console 직접 사용 대신 이 logger 를 쓴다. (ESLint no-console 규칙으로 강제)
// 출력 형식: "[LEVEL] 메시지" + 추가 인자. debug 는 개발 모드(env.isDev)에서만 출력한다.
export const logger = {
  debug(message, ...args) {
    if (env.isDev) console.debug(`[DEBUG] ${message}`, ...args);
  },
  info(message, ...args) {
    console.info(`[INFO] ${message}`, ...args);
  },
  warn(message, ...args) {
    console.warn(`[WARN] ${message}`, ...args);
  },
  error(message, ...args) {
    console.error(`[ERROR] ${message}`, ...args);
  },
};
