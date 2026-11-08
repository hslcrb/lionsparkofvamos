# 🦁 라팍 오브 바모스 · Lions Park of VAMOS

> **대구 삼성 라이온즈 파크를 브라우저 안으로 옮긴 3D 디지털 트윈,**
> **그리고 그 옆에서 함께 목청을 높이는 실시간 응원관.**

![License: MIT](https://img.shields.io/badge/license-MIT-0066B2)
![Next.js](https://img.shields.io/badge/Next.js-16-000000)
![Three.js](https://img.shields.io/badge/Three.js-r187-000000)
![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers%20%2B%20DO-F38020)

Lions Park of VAMOS는 삼성 라이온즈 팬들이 만든 **비공식 오픈소스 프로젝트**입니다.
Blender로 다시 지은 라팍(대구 삼성 라이온즈 파크)을 Three.js로 걸어 다니고 차로 달릴 수
있으며, 같은 사이트의 응원관에서는 지금 접속한 팬들과 응원 수와 춤 동작을 실시간으로
나눌 수 있습니다. 화면은 전부 정적 자산으로 CDN에서 내려가고, 실시간 동기화만 Cloudflare의
SQLite Durable Object 하나가 맡습니다. 서버를 켜 둘 필요도, 데이터베이스를 따로 둘 필요도
없습니다.

- 🏟️ **라팍월드** — `/lionspark` · 13.6 MiB Draco GLB, 75,390개 충돌체, WASD 보행과 차량 주행
- 💙 **응원관** — `/main` · WebSocket 응원 수·춤 동작 실시간 공유, 유리 엠블럼 시네마
- 🌅 **천체 대기 시뮬레이션** — 대구 위경도 기준 실제 태양 위치로 낮·밤·해돋이·노을이 흐릅니다
- ⚡ **부하 제로 엣지 아키텍처** — Next.js 정적 export + Cloudflare CDN + Durable Object

---

## 목차

1. [무엇을 만들었나](#무엇을-만들었나)
2. [화면 여행](#화면-여행)
3. [조작법](#조작법)
4. [아키텍처 — 부하 제로 엣지](#아키텍처--부하-제로-엣지)
5. [로컬에서 실행하기](#로컬에서-실행하기)
6. [검증과 테스트](#검증과-테스트)
7. [배포](#배포)
8. [저장소 구조](#저장소-구조)
9. [자산·라이선스·크레딧](#자산라이선스크레딧)
10. [기여하기](#기여하기)
11. [알려 둘 것](#알려-둘-것)

---

## 무엇을 만들었나

| | 내용 |
| --- | --- |
| **경기장 3D 재구성** | 팔각 외곽, 2단 내야석과 낮은 외야석, 흰 다각 지붕, 방패형 전광판과 별관, 큰 사다리꼴 개구부가 있는 외벽, 광장·주차장·교차로·붉은 보행로·수림·저수지, 측면 출입구의 금빛 사자 조형물까지 Blender MCP로 제작 |
| **충돌과 지형** | Blender 메시의 개별 연결 성분에서 뽑아낸 75,390개 OBB와 삼각형 바닥 인덱스. 공간 해시로 조회하며 고속 이동도 작은 단계로 나눠 얇은 벽을 통과하지 않음 |
| **보행·차량** | 걷기 7 m/s, 달리기 12 m/s, 차량 탑승·가속·조향·제동, 모바일 패드, 전체 전경, 출발점 복귀 |
| **하늘** | 대구(35.84°N, 128.68°E)의 날짜·시각으로 태양 고도와 방위를 계산해 Rayleigh·Mie 대기 산란과 태양광을 실시간 갱신. 은하 극 방향을 맞춘 야간 천체 아틀라스 |
| **응원관** | 유리 엠블럼이 떠 있는 시네마 화면, 응원 버튼, 춤 동작 3종, 접속자 수, Web Audio 기반 10% 이득의 응원가 |
| **상태 공유** | Durable Object `CheerRoom` 하나가 응원 수를 SQLite에 저장하고 접속자에게 브로드캐스트. 서버 간 조정이 필요 없는 단일 방 구조 |

## 화면 여행

### `/` — 입구
두 개의 목적지만 있는 조용한 입구입니다. **메인으로 바로 접속**은 응원관으로, **라팍월드
들어가기**는 3D 경기장으로 이어집니다. 배경은 메시 그라데이션과 유리 질감만으로 만든
Lions blue 톤이며, 네온 장식은 쓰지 않습니다. 입구에서 응원관에 들어가면 ‘나의 라이온즈’가
출력 신호의 10%까지 3초 동안 페이드 인 합니다. 시스템 음량은 건드리지 않습니다(Web Audio
`GainNode` 감쇠).

### `/main` — 응원관
- 응원 버튼을 누르면 응원 수가 모두에게 0.25초 간격으로 반영됩니다.
- **폴짝폴짝 / 손 흔들기 / 신나게 응원** 동작은 0.5초 간격으로 방에 공유됩니다.
- 지금 보고 있는 사람 수가 함께 표시됩니다.
- 둥근 음악 패널에서 응원가를 켜고 끌 수 있습니다.
- 모션 최소화 설정을 켠 사용자에게는 상시 움직임을 멈춥니다.

### `/lionspark` — 라팍월드
정적 자산만으로 도는 3D 세계입니다. 모델·충돌·텍스처·하늘은 모두 `public/models`의
정적 파일이고, 화면 계산은 브라우저에서 끝납니다. 기본 시각은 `Asia/Seoul` 기준 현재
시각이며, 낮·밤·해돋이·노을 미리보기를 고르면 그날의 지평선 근처 태양 고도부터 장면이
계속 흐릅니다. 실시간 버튼을 누르면 한국의 현재 시각으로 돌아옵니다.

### `/418` — 나는 주전자다
숨은 오류 코드 페이지입니다. Worker가 진짜 HTTP 418을 돌려줍니다. 없는 주소는 실제 404와
함께 404 페이지가 나갑니다.

## 조작법

| 동작 | 키보드 | 모바일 |
| --- | --- | --- |
| 이동 | `W` `A` `S` `D` 또는 방향키 | 화면 패드 |
| 달리기 | `Shift` (12 m/s) | 달리기 버튼 |
| 차량 탑승 / 하차 | 가까운 차 앞에서 `E` | 운전 / 하차 버튼 |
| 가속·후진 | `W` / `S` | 패드 위·아래 |
| 조향 | `A` / `D` | 패드 좌·우 |
| 제동 | `Space` | 브레이크 버튼 |
| 전체 전경 · 출발점 | 화면 버튼 | 화면 버튼 |

내릴 때는 주변에 통과 가능한 자리가 있는지 먼저 검사합니다. 운전 중에는 모바일 패드가
가속·조향을 겸합니다. `Gate 2`의 중앙 통로로 그라운드에 들어갈 수 있습니다.

## 아키텍처 — 부하 제로 엣지

```
[브라우저]
   │  정적 HTML·JS·GLB·텍스처  (Cloudflare CDN, 전 세계 엣지 캐시)
   ▼
[Cloudflare Worker]  ── 정적 자산(ASSETS) 서빙, 라우트별 실제 상태 코드(200/404/418)
   │  /api/room  (WebSocket, Origin 검사)
   ▼
[CheerRoom · SQLite Durable Object]  ── 응원 수 저장 + 접속자 브로드캐스트
```

- **Next.js 16 App Router + TypeScript(strict)**, `output: 'export'`로 `out/`에 정적
  HTML을 만듭니다. SSR·서버 액션·이미지 최적화 서버를 쓰지 않습니다.
- **Cloudflare Worker**가 `ASSETS` 바인딩으로 정적 자산을 서빙하고, `/`, `/main`,
  `/lionspark`, `/418`에는 각각의 HTML을, 나머지 HTML 요청에는 실제 404를 돌려줍니다.
  GET·HEAD 외에는 405입니다.
- **Durable Object `CheerRoom`**은 방 하나(`cinema`)에 하나입니다. SQLite에 응원 수
  한 줄만 저장하고, 접속자 수와 응원·춤 이벤트를 메모리 소켓으로 브로드캐스트합니다.
  클라이언트 메시지는 256바이트 이하, 알려진 타입만 통과시킵니다.
- **부하 특성**: 페이지 요청은 CDN 캐시에서 끝나고, Worker는 HTML 상태 코드와 WebSocket
  업그레이드만 처리합니다. 영속 저장은 응원 수 증가 한 번뿐이라 트래픽이 몰려도 병목이
  생기지 않습니다.
- **저장하는 정보**: 응원 수 하나와 현재 접속 소켓 수. 계정·쿠키·개인정보·채팅 로그를
  저장하지 않습니다.

## 로컬에서 실행하기

**요구 사항** — Node.js 22 이상, npm. (Cloudflare 계정은 배포할 때만 필요합니다.)

```sh
git clone https://github.com/hslcrb/lionsparkofvamos.git
cd lionsparkofvamos
npm ci
npm run local
```

`http://127.0.0.1:8787`에서 **배포와 같은 구성**(정적 페이지 + Worker + WebSocket)을 그대로
확인할 수 있습니다. 종료는 `Ctrl+C`. 로컬 응원 수는 `.wrangler/` 아래에 저장되어 운영
데이터와 섞이지 않습니다.

화면을 빠르게 고칠 때는 위 서버를 켜 둔 채 다른 터미널에서:

```sh
npm run dev        # http://127.0.0.1:3000, /api/* 는 로컬 Worker(8787)로 프록시
```

### 주요 스크립트

| 명령 | 설명 |
| --- | --- |
| `npm run dev` | Next 개발 서버 (3000) |
| `npm run build` | 정적 export → `out/` |
| `npm run local` | 빌드 후 `wrangler dev --local` (8787) |
| `npm run preview` | 빌드 없이 로컬 Worker만 실행 |
| `npm run typecheck` | 앱·Worker 타입 검사 |
| `npm run lint` · `npm run format:check` | ESLint · Prettier 검사 |
| `npm test` | 단위 테스트 (`tsx --test`) |
| `npm run check` | 타입·린트·포맷·테스트·빌드 전체 |
| `npm run verify:local` | 실제 로컬 서버로 페이지·상태 코드·음원·WebSocket 2클라이언트 검증 |
| `npm run deploy` | 빌드 후 `wrangler deploy` |

## 검증과 테스트

```sh
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
```

전체는 `npm run check` 한 번입니다. `npm run preview`를 켜 둔 상태에서 `npm run verify:local`을
실행하면 내보낸 페이지, 404·418 상태 코드, 음원 응답, Next 탐색 데이터, 그리고 두 개의
WebSocket 클라이언트가 응원·춤을 실제로 공유하는지까지 확인합니다. 이 검사는 로컬 응원 수를
한 번 올립니다.

GitHub Actions 워크플로는 `.github/check.yml.txt`로 보관되어 있습니다. GitHub App 권한으로는 워크플로 파일을 만들 수
없어 `workflows/` 밖에 두었습니다. Actions를 쓰려면 `.github/workflows/check.yml`로 옮겨
커밋하고(워크플로 권한이 있는 계정으로) Actions를 활성화하면 됩니다.

## 배포

무료 Cloudflare 계정으로 충분합니다.

```sh
npx wrangler login
npm run deploy
```

- `wrangler.jsonc`의 Worker 이름은 `lionsparkofvamos`, Durable Object 클래스는 `CheerRoom`,
  SQLite 마이그레이션 태그는 `v1`입니다.
- 이미 응원 데이터가 있는 방에 붙일 때는 **클래스 이름·인스턴스 이름·마이그레이션을 바꾸지
  마세요.** 바꾸면 기존 응원 수가 새 방으로 이어지지 않습니다.
- Cloudflare 대시보드에서 저장소를 연결하면 `main` 푸시마다 `npm run check` 후 자동 배포할
  수 있습니다.

## 저장소 구조

```
src/
  app/                     라우트: /, /main, /lionspark, /418, 404, error
  components/              응원 카드, 동작 패널, 유리 엠블럼, 음악 공급자·제어 UI
  features/lionspark/      런타임(모델·충돌·차량), 물리, 지형 인덱스, 천체·대기, HUD
  hooks/                   방 연결·재연결, 응원 버스트 타이머
  cinema/scene.ts          Three.js 장면 생성·동작·자원 해제
  room.ts                  클라이언트·서버 공용 메시지 타입과 검증
worker/
  index.ts                 자산 서빙·라우트·상태 코드·/api/room
  cheer-room.ts            CheerRoom SQLite Durable Object
test/                      물리·천체·지형·음악·프로토콜 단위 테스트
scripts/verify-local.ts    실제 로컬 서버 통합 검증
public/
  models/                  lionspark.glb, 충돌 JSON, 하늘 텍스처, 크레딧
  draco/                   Draco 디코더
assets/blender/            재구성 소스(v3), 빌드 스크립트, 참고 사진, 텍스처
docs/                      디자인·응원 문구·마이그레이션 계획
source-materials/          제공받은 SVG·디자인 원본
```

경기장 모델은 저장소 용량 때문에 **최신 v3 블렌드 파일만** 포함합니다. v1·v2 블렌드와 구버전
아카이브는 제외되어 있지만, 빌드 스크립트는 v1·v2·v3 모두 남겨 두어 재구성 과정을 그대로 따라갈
수 있습니다. 순서와 주의 사항은 [`assets/blender/README.md`](assets/blender/README.md)에
정리했습니다.

## 자산·라이선스·크레딧

- **코드**: [MIT](LICENSE) · Copyright (c) 2026 Lions Park of VAMOS contributors
- **삼성 라이온즈·VAMOS 로고, 구단 응원가 음원, 경기장 사인 원본**: 원 권리자에게 있으며
  MIT 적용 대상이 아닙니다. 이 저장소는 **비공식 팬 프로젝트**로만 사용합니다.
  자세한 범위는 [NOTICE.md](NOTICE.md)와 [public/models/credits.txt](public/models/credits.txt).
- **하늘 사진** — Kloofendal 38d Partly Cloudy Pure Sky, Greg Zaal & Jarod Guest, Poly Haven, CC0
- **콘크리트 텍스처** — Concrete Pavement 03, Charlotte Baglioni, Poly Haven, CC0
- **대기 산란** — three.js `Sky` (Preetham 모델), MIT
- **태양 위치·일출·일몰** — NOAA / Meeus 근사식
- **은하 좌표 참고** — Astropy Galactic frame
- **야간 천체 아틀라스** — `assets/blender/celestial_sky_texture.py`로 만든 절차적 아트워크
  (통계적 별 배치이며 실제 성표가 아닙니다)
- **Draco** — Apache License 2.0

## 기여하기

팬의 손으로 더 나아집니다. 오타, 문서, 접근성, 물리, 셰이더, 성능 무엇이든 환영합니다.

1. 이슈에서 무엇을 바꿀지 먼저 이야기해 주세요(큰 변경은 특히).
2. `main`에서 브랜치를 따고(`feat/…`, `fix/…`, `docs/…`) 작업합니다.
3. 올리기 전에 `npm run check`를 통과시킵니다.
4. PR에는 **무엇을, 왜, 어떻게 확인했는지**를 적습니다. 스크린샷이 있으면 더 좋습니다.

자세한 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md)에 있습니다.

## 알려 둘 것

- 이 프로젝트는 **삼성 라이온즈 구단과 무관한 비공식 팬 프로젝트**입니다. 구단의 승인·후원을
  받지 않았습니다.
- 경기장은 제공된 항공 사진·평면도·야간 외벽 사진을 토대로 한 **해석적 재구성**입니다. 실측
  도면 기반의 측량적 디지털 트윈이 아니며, 치수·동선·주변 배치는 실제와 다를 수 있습니다.
- 응원가 음원과 구단 로고는 팬 프로젝트 시연 목적의 사용입니다. 권리자의 요청이 있으면
  해당 자산을 제거합니다.
- 이 저장소에는 개인정보·대화 기록·비밀 키가 들어 있지 않습니다. 기여할 때도 넣지 마세요.

---

**GO LIONS!** 💙🤍 — 라팍에서, 그리고 브라우저에서.
