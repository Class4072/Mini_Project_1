import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMap, loadMapSdk } from "./mapProvider";
import RegionMap from "./RegionMap";
import { NATIONAL_VIEW, REGION_GEO } from "./regionGeo";

jest.mock("./mapProvider");

// regionGeo 에 있는 17개 코드. 이름은 테스트용.
const REGIONS = Object.keys(REGION_GEO).map((code) => ({ code, name: `지역${code}` }));
REGIONS.find((r) => r.code === "6").name = "부산";
REGIONS.find((r) => r.code === "39").name = "제주";
REGIONS.find((r) => r.code === "32").name = "강원";

const handle = () => createMap.mock.results[0].value;
const lastLabels = () => handle().setRegionLabels.mock.calls.at(-1)[0];

async function renderReady(props) {
  const utils = render(<RegionMap regions={REGIONS} onSelectRegion={jest.fn()} {...props} />);
  await waitFor(() => expect(handle().setRegionLabels).toHaveBeenCalled());
  return utils;
}

describe("RegionMap", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    loadMapSdk.mockResolvedValue();
  });

  it("불러오는 동안 안내 문구를 보여주고, 준비되면 전국 보기로 지도를 만든다", async () => {
    render(<RegionMap regions={REGIONS} selectedRegionCode={null} onSelectRegion={jest.fn()} />);
    expect(screen.getByText("지도를 불러오는 중이에요")).toBeInTheDocument();

    await waitFor(() => expect(createMap).toHaveBeenCalledTimes(1));
    expect(createMap).toHaveBeenCalledWith(expect.any(HTMLElement), {
      center: { lat: 36.2, lng: 127.9 },
      level: 12,
    });
    expect(createMap.mock.calls[0][1]).toEqual(NATIONAL_VIEW);
    expect(screen.queryByText("지도를 불러오는 중이에요")).not.toBeInTheDocument();
  });

  it("지역 미선택이면 라벨 17개를 모두 default 로 넘기고, 라벨 클릭은 onSelectRegion 을 부른다", async () => {
    const onSelectRegion = jest.fn();
    await renderReady({ selectedRegionCode: null, onSelectRegion });

    const labels = lastLabels();
    expect(labels).toHaveLength(17);
    expect(labels.every((label) => label.state === "default")).toBe(true);
    expect(handle().focus).not.toHaveBeenCalled();

    handle().setRegionLabels.mock.calls.at(-1)[1].onClick("6");
    expect(onSelectRegion).toHaveBeenCalledWith("6");
  });

  it("라벨은 label 좌표에 그리고, label 이 없으면 center 에 그린다", async () => {
    await renderReady({ selectedRegionCode: null });

    const labels = lastLabels();
    expect(labels.find((label) => label.code === "6")).toEqual({
      code: "6",
      name: "부산",
      lat: 35.1,
      lng: 129.1,
      state: "default",
    });
    expect(labels.find((label) => label.code === "32")).toEqual({
      code: "32",
      name: "강원",
      ...REGION_GEO["32"].center,
      state: "default",
    });
  });

  it("지역을 고르면 center 로 focus 하고 나머지 라벨은 dimmed 로 넘긴다", async () => {
    const { rerender } = await renderReady({ selectedRegionCode: "6" });

    expect(handle().focus).toHaveBeenLastCalledWith(
      { lat: 35.1798, lng: 129.075 },
      REGION_GEO["6"].level,
    );
    const labels = lastLabels();
    expect(labels.filter((label) => label.state === "selected").map((l) => l.code)).toEqual(["6"]);
    expect(labels.filter((label) => label.state === "dimmed")).toHaveLength(16);
    expect(screen.getByText("부산")).toBeInTheDocument();

    // 지역 바꾸기 팝업으로 지역이 바뀌면 새 지역으로 다시 focus
    rerender(<RegionMap regions={REGIONS} selectedRegionCode="39" onSelectRegion={jest.fn()} />);
    const jeju = REGION_GEO["39"];
    expect(handle().focus).toHaveBeenLastCalledWith(jeju.center, jeju.level);
    expect(lastLabels().find((label) => label.code === "39").state).toBe("selected");
    expect(screen.getByText("제주")).toBeInTheDocument();
  });

  it("regionGeo 에 없는 코드는 라벨을 그리지 않고 경고만 남긴다", async () => {
    const warn = jest.spyOn(console, "warn").mockImplementation(() => {});
    await renderReady({
      regions: [...REGIONS, { code: "999", name: "없는지역" }],
      selectedRegionCode: null,
    });

    expect(lastLabels()).toHaveLength(17);
    expect(lastLabels().some((label) => label.code === "999")).toBe(false);
    expect(warn).toHaveBeenCalledWith(expect.stringContaining("999"));
    warn.mockRestore();
  });

  describe("제주 바로가기", () => {
    const shortcut = () => screen.queryByRole("button", { name: "제주 선택" });

    it("전국 보기에서 보이고, 누르면 제주 코드로 onSelectRegion 을 부른다", async () => {
      const onSelectRegion = jest.fn();
      await renderReady({ selectedRegionCode: null, onSelectRegion });

      expect(shortcut()).toBeInTheDocument();
      fireEvent.click(shortcut());
      expect(onSelectRegion).toHaveBeenCalledWith("39");
      // 지도 위 실제 좌표 라벨도 그대로 그린다
      expect(lastLabels().some((label) => label.code === "39")).toBe(true);
    });

    it("지역이 선택되면 숨긴다", async () => {
      const { rerender } = await renderReady({ selectedRegionCode: null });
      expect(shortcut()).toBeInTheDocument();

      rerender(<RegionMap regions={REGIONS} selectedRegionCode="6" onSelectRegion={jest.fn()} />);
      expect(shortcut()).not.toBeInTheDocument();
    });

    it("지도 로딩 중에는 보이지 않는다", () => {
      loadMapSdk.mockReturnValue(new Promise(() => {}));
      render(<RegionMap regions={REGIONS} selectedRegionCode={null} onSelectRegion={jest.fn()} />);
      expect(screen.getByText("지도를 불러오는 중이에요")).toBeInTheDocument();
      expect(shortcut()).not.toBeInTheDocument();
    });

    it("지도 불러오기에 실패하면 보이지 않는다", async () => {
      loadMapSdk.mockRejectedValue(new Error("load failed"));
      render(<RegionMap regions={REGIONS} selectedRegionCode={null} onSelectRegion={jest.fn()} />);
      await screen.findByText("지도를 불러오지 못했어요. 왼쪽 목록에서 지역을 골라주세요.");
      expect(shortcut()).not.toBeInTheDocument();
    });
  });

  it("SDK 를 불러오지 못하면 실패 문구를 보여준다", async () => {
    loadMapSdk.mockRejectedValue(new Error("load failed"));
    render(<RegionMap regions={REGIONS} selectedRegionCode={null} onSelectRegion={jest.fn()} />);

    expect(
      await screen.findByText("지도를 불러오지 못했어요. 왼쪽 목록에서 지역을 골라주세요."),
    ).toBeInTheDocument();
    expect(createMap).not.toHaveBeenCalled();
  });

  it("사라질 때 destroy 를 부른다", async () => {
    const { unmount } = await renderReady({ selectedRegionCode: null });
    unmount();
    expect(handle().destroy).toHaveBeenCalledTimes(1);
  });
});
