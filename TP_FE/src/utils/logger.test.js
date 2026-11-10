import { env } from "../config/env";
import { logger } from "./logger";

describe("logger", () => {
  const original = { ...env };
  let spies;

  beforeEach(() => {
    spies = Object.fromEntries(
      ["debug", "info", "warn", "error"].map((level) => [
        level,
        jest.spyOn(console, level).mockImplementation(() => {}),
      ]),
    );
  });

  afterEach(() => {
    Object.assign(env, original);
    jest.restoreAllMocks();
  });

  it.each([
    ["info", "[INFO] 메시지"],
    ["warn", "[WARN] 메시지"],
    ["error", "[ERROR] 메시지"],
  ])("%s 는 레벨 표시를 붙여 같은 이름의 console 메서드로 출력한다", (level, expected) => {
    logger[level]("메시지");
    expect(spies[level]).toHaveBeenCalledWith(expected);
  });

  it("추가 인자를 그대로 넘긴다", () => {
    const error = new Error("boom");
    logger.error("요청 실패", error, { id: 1 });
    expect(spies.error).toHaveBeenCalledWith("[ERROR] 요청 실패", error, { id: 1 });
  });

  it("debug 는 개발 모드에서만 출력한다", () => {
    env.isDev = false;
    logger.debug("숨김");
    expect(spies.debug).not.toHaveBeenCalled();

    env.isDev = true;
    logger.debug("보임", 42);
    expect(spies.debug).toHaveBeenCalledWith("[DEBUG] 보임", 42);
  });
});
