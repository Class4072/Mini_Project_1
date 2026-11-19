# 도메인과 Cloudflare 터널

맥미니의 서비스를 공유기 포트포워딩 없이 인터넷에 공개하는 방법입니다.

## 현재 구성

| 항목 | 값 |
| :--- | :--- |
| 도메인 | `ricebug.dev` (Cloudflare, Free 플랜) |
| 터널 이름 | `macmini` |
| 설정 파일 | 맥미니 `~/.cloudflared/config.yml` |
| 자동 시작 | `~/Library/LaunchAgents/dev.ricebug.cloudflared.plist` (로그인 시 시작, 죽으면 재시작) |
| 로그 | `~/Library/Logs/cloudflared.log` |
| 연결된 주소 | `tp.ricebug.dev` → `http://127.0.0.1:80` (TP FE) |

- 공개하는 주소는 FE 하나입니다. FE(nginx)가 `/api` 를 내부에서 BE 로 넘기므로 BE·AI 는 공개하지 않습니다.
- Cloudflare 대시보드에서 **Always Use HTTPS** 를 켜 두었습니다 (http 접속 → https 로 이동).
- 공개 범위는 누구나입니다. 일정 공유 링크(F-26)를 받은 사람이 로그인 없이 열어야 하기 때문입니다.

## 주소 이름 규칙

`<프로젝트>.ricebug.dev`, 같은 프로젝트에서 용도를 나눌 때는 `<프로젝트>-<용도>.ricebug.dev`.

- 점(.)을 두 단계 이상 쓰면(`tp.project.ricebug.dev`, `dev.tp.ricebug.dev`) Cloudflare 무료 인증서(`*.ricebug.dev`)가 적용되지 않아 HTTPS 가 안 됩니다. 하이픈으로 구분합니다.

## 새 주소 추가 (다른 프로젝트)

1. `~/.cloudflared/config.yml` 의 마지막 `http_status:404` 규칙 **앞에** 추가

   ```yaml
   - hostname: <이름>.ricebug.dev
     service: http://127.0.0.1:<포트>
   ```

2. DNS 연결: `cloudflared tunnel route dns macmini <이름>.ricebug.dev`
   (같은 이름의 DNS 레코드가 이미 있으면 충돌하므로 대시보드에서 먼저 지움)
3. 터널 재시작: `launchctl kickstart -k gui/$(id -u)/dev.ricebug.cloudflared`
4. 서비스 포트는 `127.0.0.1` 에만 열어 터널로만 들어오게 합니다.

## 접속이 안 될 때

- **새 주소를 만든 직후 안 열림:** 레코드가 생기기 전에 조회한 "없음" 결과가 DNS 캐시에 남은 경우가 많습니다.
  - Windows: `ipconfig /flushdns` 후 브라우저 완전 종료·재실행
  - macOS: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
  - 확인: `nslookup tp.ricebug.dev 1.1.1.1` 은 되는데 `nslookup tp.ricebug.dev` 가 안 되면 공유기·통신사 DNS 캐시 문제 (시간이 지나면 풀림)
- **Cloudflare 오류 페이지(502·1033 등):** 터널이나 FE 컨테이너가 내려간 경우. 맥미니에서 `docker compose ps`, `cloudflared tunnel info macmini`, 로그 확인
- **페이지는 뜨는데 지도가 안 나옴:** Kakao Developers 에 해당 도메인이 등록됐는지 확인
