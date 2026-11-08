# 🦁 라팍 오브 바모스 · Lions Park of VAMOS

> **대구 삼성 라이온즈 파크와 그 일대를 브라우저 안으로 옮긴 3D 디지털 트윈,**
> **그리고 그 옆에서 함께 목청을 높이는 실시간 응원관.**

![License: MIT](https://img.shields.io/badge/license-MIT-0066B2)
![Next.js](https://img.shields.io/badge/Next.js-16-000000)
![Three.js](https://img.shields.io/badge/Three.js-r187-000000)
![Blender](https://img.shields.io/badge/Blender-4.2-E87D0D)
![Self-hosted](https://img.shields.io/badge/self--hosted-Docker%20%7C%20Node%20%7C%20Vercel%20%7C%20Pages-2ea44f)

Lions Park of VAMOS는 삼성 라이온즈 팬들이 만든 **비공식 오픈소스 프로젝트**입니다.
Blender로 절차적으로 다시 지은 라팍(대구 삼성 라이온즈 파크)과 대공원역·달구벌대로 일대를
Three.js로 걸어 다니고 차로 달릴 수 있으며, 같은 사이트의 응원관에서는 접속한 팬들과 응원 수와
춤 동작을 실시간으로 나눌 수 있습니다.

**개인 계정·도메인·인증서에 묶여 있지 않습니다.** 클론한 뒤 `docker compose up` 한 번, 또는
`npm run build`로 나온 `out/`을 아무 정적 호스트에 올리면 바로 내 사이트가 됩니다.
Blender 파일도 함께 들어 있어, 모델을 열어 고치고 다시 내보낼 수 있습니다.

- 🏟️ **라팍월드** — `/lionspark` · 12.0 MB Draco GLB, 9,376개 충돌체, 36,423석, WASD 보행과 차량 주행
- 🎨 **삼성 라이온즈 전광판** — 36 m × 20.4 m 메인 LED 월, 1·3루 2층 난간 띠전광판, 외야 펜스와 팀스토어에 2026 한국시리즈 승리 그래픽을 발광 텍스처로 매핑
- 🚶 **경기장 안쪽** — 걷는 1·2층 콘코스와 계단, 땅땅치킨·로사안젤라·라팍 편의점, 구역 안내판(블루존·익사이팅존 등), VIP 스위트·프레스 박스, 덕아웃 장비와 외야 불펜
- 🛣️ **실제 주소와 주변 지리** — 야구전설로 1 도로명판·달구벌대로 안내표지, 연호지 수면, 수성알파시티 타워, 대구스타디움·대구미술관 원경 실루엣
- 🏙️ **초극실사 확장** — 대공원역 4·5번 출구, 달구벌대로 10차선, P1·P2 주차장, 광장, 연호산 수림
- 💙 **응원관** — `/main` · WebSocket 응원 수·춤 동작 실시간 공유, 유리 엠블럼 시네마
- 🌅 **천체 대기 시뮬레이션** — 대구 위경도 기준 실제 태양 위치로 낮·밤이 흐르고, 🌅 일출(태양 5°)·☀️ 낮·🌇 노을(태양 8°)·🌙 밤 네 장면을 버튼 한 번에 전환합니다
- 🐳 **어디서나 자체 호스팅** — Docker, Node, VPS·Nginx, Vercel, Cloudflare, GitHub Pages

---

## 목차

1. [무엇을 만들었나](#무엇을-만들었나)
2. [30초 만에 내 사이트로](#30초-만에-내-사이트로)
3. [화면 여행](#화면-여행)
4. [조작법](#조작법)
5. [아키텍처](#아키텍처)
6. [로컬에서 실행하기](#로컬에서-실행하기)
7. [검증과 테스트](#검증과-테스트)
8. [배포](#배포)
9. [블렌더 파이프라인](#블렌더-파이프라인)
10. [저장소 구조](#저장소-구조)
11. [자산·라이선스·크레딧](#자산라이선스크레딧)
12. [기여하기](#기여하기)
13. [알려 둘 것](#알려-둘-것)

---

## 무엇을 만들었나

| | 내용 |
| --- | --- |
| **경기장** | 대한민국 유일의 팔각 다이아몬드 구장. 2단 내야석과 낮은 외야석(36,423석), 캔틸레버 지붕과 백색 트러스, 커다란 사다리꼴 개구부가 있는 외벽, 3루 블루존과 1루 원정석, 덕아웃, 백스톱, 페어폴 |
| **그라운드** | 모잉 스트라이프 잔디, 내야 흙, 마운드·베이스·파울라인, 외야 펜스와 홈런 라인, 외야 잔디석과 모래놀이터 |
| **전광판** | 외야 우측 36 m × 20.4 m LED 스크린과 철골 프레임, 후면 브랜드 월 |
| **일대** | 달구벌대로 10차선(중앙분리대 화단·가로수·가로등·횡단보도·교통섬), 야구전설로, 대공원역 4·5번 출구(유리 캐노피·계단·역명 표지), P1·P2 주차장, 야구전설로 광장(대계단·매표소·팀스토어·황금 사자상·키오스크), 연호산 녹지 구릉 |
| **충돌과 지형** | Blender 메시의 개별 연결 성분에서 뽑아낸 9,376개 OBB와 삼각형 바닥 인덱스. 공간 해시로 조회하며 고속 이동도 작은 단계로 나눠 얇은 벽을 통과하지 않음 |
| **보행·차량** | 걷기 7 m/s, 달리기 12 m/s, 차량 탑승·가속·조향·제동, 모바일 패드, 전체 전경, 출발점 복귀 |
| **하늘** | 대구(35.84°N, 128.68°E)의 날짜·시각으로 태양 고도와 방위를 계산해 Rayleigh·Mie 대기 산란과 태양광을 실시간 갱신. 은하 극 방향을 맞춘 야간 천체 아틀라스 |
| **응원관** | 유리 엠블럼이 떠 있는 시네마 화면, 응원 버튼, 춤 동작 3종, 접속자 수, Web Audio 기반 10% 이득의 응원가 |
| **자체 호스팅** | 정적 export + 의존성 없는 Node 서버(Docker 포함). Cloudflare 없이도 실시간 응원이 동작 |

### 모델 제작 방식

`assets/blender/lionspark_v5_build.py` **하나로** 경기장·광장·도로·역·주차장·수림과 콘코스 내부까지 모두
절차적으로 짓습니다. 외부 애드온이나 Blender MCP 세션 없이 `blender --background --python`으로
재현되며, 재질은 전부 Principled BSDF + 패킹된 이미지 텍스처라 GLB 하나에 결과물이 담깁니다.
자세한 사용법은 [BLENDER_GUIDE.md](BLENDER_GUIDE.md)에 있습니다.

## 30초 만에 내 사이트로

```sh
git clone https://github.com/hslcrb/lionsparkofvamos.git
cd lionsparkofvamos
docker compose up --build
# → http://localhost:8080
```

Docker가 없다면:

```sh
npm ci && npm run build      # Node.js 22 이상
node server/standalone.mjs   # 정적 서버 + WebSocket 응원방, 기본 8080
```

정적 호스트(Vercel·Cloudflare Pages·GitHub Pages·S3)에 올릴 때는 `out/` 디렉터리만 있으면
됩니다. 다만 그 경우 실시간 응원(접속자 수·누적 응원)은 동작하지 않고, 응원 버튼과 춤은 내
화면에서만 반응합니다. 호스트별 자세한 절차는 **[DEPLOYMENT.md](DEPLOYMENT.md)** 를 보세요.

| 하고 싶은 것 | 명령 |
| --- | --- |
| 도커로 한 번에 | `docker compose up --build` |
| 노드 서버로 | `npm run build && npm run serve` |
| Cloudflare Workers(내 계정) | `npx wrangler login && npm run deploy` |
| Vercel | `npx vercel --prod` |
| GitHub Pages 하위 경로 | `NEXT_PUBLIC_BASE_PATH=/저장소이름 npm run build` + `.nojekyll` |

## 화면 여행

### `/` — 입구
두 개의 목적지만 있는 조용한 입구입니다. **메인으로 바로 접속**은 응원관으로, **라팍월드
들어가기**는 3D 경기장으로 이어집니다. 배경은 메시 그라데이션과 유리 질감만으로 만든
Lions blue 톤이며, 네온 장식은 쓰지 않습니다. 입구에서 응원관에 들어가면 ‘나의 라이온즈’가
출력 신호의 10%까지 3초 동안 페이드 인 합니다. 시스템 음량은 건드리지 않습니다.

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

광장 중앙에서 출발해 **게이트 2**의 중앙 통로로 그라운드에 들어갈 수 있고, 달구벌대로에
세워 둔 차에 타면 야구전설로와 주차장을 달릴 수 있습니다.

### `/418` — 나는 주전자다
숨은 오류 코드 페이지입니다. Worker/Node 서버가 진짜 HTTP 418을 돌려줍니다. 없는 주소는
실제 404와 함께 404 페이지가 나갑니다.

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
가속·조향을 겸합니다.

## 아키텍처

```
[브라우저]
   │  정적 HTML·JS·GLB·텍스처   (호스트의 CDN·정적 서버)
   ▼
[정적 자산]  ── out/ : 페이지, 3D 모델, 충돌 데이터, 하늘 텍스처
   │  /api/room  (WebSocket, 선택)
   ▼
[응원방]  ── ① Cloudflare Durable Object ② 내장 Node 서버 ③ 없음(정적 호스트)
```

- **Next.js 16 App Router + TypeScript(strict)**, `output: 'export'`로 `out/`에 정적
  HTML을 만듭니다. SSR·서버 액션·이미지 최적화 서버를 쓰지 않습니다.
- **정적 자산 서버**는 세 가지 중 하나입니다.
  1. **Cloudflare Worker** — `ASSETS` 바인딩으로 정적 자산을 서빙하고 `/api/room`을
     `CheerRoom` Durable Object로 넘깁니다. `/`, `/main`, `/lionspark`, `/418`에 각각의
     HTML을, 나머지 HTML 요청에는 실제 404를 돌려줍니다.
  2. **내장 Node 서버**(`server/standalone.mjs`) — 의존성 없이 같은 라우팅·상태 코드·
     WebSocket 프로토콜을 구현합니다. Docker 이미지가 이 서버를 씁니다.
  3. **정적 호스트** — 실시간 응원 없이 페이지만 서빙합니다.
- **응원 상태** — 방 하나(`cinema`)에 응원 수 한 줄과 접속 소켓만 있습니다. 클라이언트
  메시지는 256바이트 이하, 알려진 타입만 통과시킵니다. 계정·쿠키·개인정보·채팅 로그를
  저장하지 않습니다.
- **하위 경로 배포** — `NEXT_PUBLIC_BASE_PATH` 하나로 `basePath`와 모델·음원·Draco 경로가
  함께 이동합니다(`src/asset-path.ts`).

## 로컬에서 실행하기

**요구 사항** — Node.js 22 이상, npm. (Docker를 쓸 경우 Docker만 있으면 됩니다.)

```sh
git clone https://github.com/hslcrb/lionsparkofvamos.git
cd lionsparkofvamos
npm ci
npm run local
```

`http://127.0.0.1:8787`에서 **배포와 같은 구성**(정적 페이지 + Worker + WebSocket)을 그대로
확인할 수 있습니다. 종료는 `Ctrl+C`. 로컬 응원 수는 `.wrangler/` 아래에 저장됩니다.

Cloudflare 없이 도는 구성도 있습니다.

```sh
npm run build
npm run serve      # http://127.0.0.1:8080, 내장 Node 서버
```

화면을 빠르게 고칠 때는 위 서버를 켜 둔 채 다른 터미널에서:

```sh
npm run dev        # http://127.0.0.1:3000, /api/* 는 로컬 Worker(8787)로 프록시
```

### 주요 스크립트

| 명령 | 설명 |
| --- | --- |
| `npm run dev` | Next 개발 서버 (3000) |
| `npm run build` | 정적 export → `out/` |
| `npm run serve` | 내장 Node 서버로 `out/` 서빙 (8080) |
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
WebSocket 클라이언트가 응원·춤을 실제로 공유하는지까지 확인합니다.

GitHub Actions 워크플로는 `.github/check.yml.txt`로 보관되어 있습니다. GitHub App 권한으로는
워크플로 파일을 만들 수 없어 `workflows/` 밖에 두었습니다. Actions를 쓰려면
`.github/workflows/check.yml`로 옮겨 커밋하고(워크플로 권한이 있는 계정으로) Actions를
활성화하면 됩니다. 같은 이유로 GitHub Pages 배포 워크플로 예시는
[DEPLOYMENT.md](DEPLOYMENT.md)에만 두었습니다.

## 배포

| 호스트 | 3D | 실시간 응원 | 문서 |
| --- | --- | --- | --- |
| Docker / docker compose | ✅ | ✅ | [DEPLOYMENT.md §1](DEPLOYMENT.md#1-docker--가장-빠른-자체-호스팅) |
| Node 서버 · VPS · NAS · Railway | ✅ | ✅ | [§2](DEPLOYMENT.md#2-nodejs-서버--vps--nas) |
| Cloudflare Workers(내 계정) | ✅ | ✅ | [§3](DEPLOYMENT.md#3-cloudflare-workers--원래-구성본인-계정) |
| Vercel | ✅ | ⚠️ 로컬 응원만 | [§4](DEPLOYMENT.md#4-vercel) |
| Cloudflare Pages · Netlify · S3 | ✅ | ⚠️ 로컬 응원만 | [§5](DEPLOYMENT.md#5-cloudflare-pages--netlify--s3-등-정적-호스트) |
| GitHub Pages | ✅ | ⚠️ 로컬 응원만 | [§6](DEPLOYMENT.md#6-github-pages) |
| 정적 Nginx | ✅ | ⚠️ 로컬 응원만 | [§7](DEPLOYMENT.md#7-정적-nginx) |

Cloudflare를 쓴다면 무료 계정으로 충분합니다.

```sh
npx wrangler login
npm run deploy
```

- `wrangler.jsonc`의 Worker 이름은 `lionsparkofvamos`, Durable Object 클래스는 `CheerRoom`,
  SQLite 마이그레이션 태그는 `v1`입니다.
- 이미 응원 데이터가 있는 방에 붙일 때는 **클래스 이름·인스턴스 이름·마이그레이션을 바꾸지
  마세요.** 바꾸면 기존 응원 수가 새 방으로 이어지지 않습니다.
- 계정 ID·도메인·인증서는 저장소에 없습니다. 원하는 호스트에 원하는 도메인으로 붙이면 됩니다.

## 블렌더 파이프라인

```sh
blender --background --python assets/blender/lionspark_v5_build.py
```

- `assets/blender/lionspark_v5_build.py` — 경기장·광장·도로·역·주차장·수림·콘코스를 절차적으로
  생성하고 Draco GLB, 충돌체 JSON, 씬 JSON, `.blend`, 네 가지 하늘 미리보기 렌더를 한 번에 내보냅니다.
- `assets/blender/lionspark-v5.blend` — 텍스처가 패킹된 편집용 씬(약 22 MB).
- `scripts/prepare-v5-graphics.py` — 제공받은 삼성 라이온즈 승리 그래픽을 LED 월·띠전광판·배너
  텍스처로 합성합니다(`assets/graphics/` → `assets/blender/textures/brand-*.jpg`).
- 좌표계는 미터·Blender Z-up이며, 웹은 `(x, z, −y)`로 받습니다.
- 오브젝트 이름 규칙(`WalkSurface*`, `Seat_*`, `Night_*`, `Driveable_Car`)이 런타임 동작과
  연결되어 있습니다. 열람·수정·Unity/Unreal/Three.js 내보내기 방법은
  **[BLENDER_GUIDE.md](BLENDER_GUIDE.md)** 에 정리했습니다.

## 저장소 구조

```
src/
  app/                     라우트: /, /main, /lionspark, /418, 404, error
  components/              응원 카드, 동작 패널, 유리 엠블럼, 음악 공급자·제어 UI
  features/lionspark/      런타임(모델·충돌·차량), 물리, 지형 인덱스, 천체·대기, HUD
  hooks/                   방 연결·재연결, 응원 버스트 타이머
  asset-path.ts            하위 경로 배포용 자산 경로
  cinema/scene.ts          Three.js 장면 생성·동작·자원 해제
  room.ts                  클라이언트·서버 공용 메시지 타입과 검증
worker/
  index.ts                 자산 서빙·라우트·상태 코드·/api/room
  cheer-room.ts            CheerRoom SQLite Durable Object
server/
  standalone.mjs           의존성 없는 Node 정적 서버 + WebSocket 응원방
deploy/nginx.conf          정적 Nginx 설정 예시
test/                      물리·천체·지형·음악·프로토콜·자산 경로 단위 테스트
scripts/verify-local.ts    실제 로컬 서버 통합 검증
public/
  models/                  lionspark.glb, 충돌 JSON, 하늘 텍스처, 크레딧
  draco/                   Draco 디코더
assets/blender/            v5 빌드 스크립트·씬, 폰트, 참고 사진, 텍스처, 매니페스트
assets/graphics/           제공받은 삼성 라이온즈 승리 그래픽 원본과 합성 기록
docs/                      디자인·응원 문구·로드맵
source-materials/          제공받은 SVG·디자인 원본
Dockerfile                 멀티스테이지 빌드 + Node 런타임
docker-compose.yml         1분 자체 호스팅
DEPLOYMENT.md              호스트별 배포 매뉴얼
BLENDER_GUIDE.md           블렌더 열람·수정·내보내기 가이드
```

경기장 모델은 저장소 용량 때문에 **v5·v4·v3 블렌드만** 포함합니다(최신 v5, 직전 v4, 역사 기록 v3).
v1·v2 블렌드는 제외되어 있지만 빌드 스크립트는 모두 남겨 두어 재구성 과정을 따라갈 수 있습니다. 순서와
주의 사항은 [`assets/blender/README.md`](assets/blender/README.md)에 정리했습니다.

## 자산·라이선스·크레딧

- **코드·모델·스크립트**: [MIT](LICENSE) · Copyright (c) 2026 Lions Park of VAMOS contributors
- **삼성 라이온즈·VAMOS 로고, 구단 응원가 음원, 경기장 사인 원본**: 원 권리자에게 있으며
  MIT 적용 대상이 아닙니다. 이 저장소는 **비공식 팬 프로젝트**로만 사용합니다.
  자세한 범위는 [NOTICE.md](NOTICE.md)와 [public/models/credits.txt](public/models/credits.txt).
- **폰트** — Noto Sans KR(Adobe, SIL OFL 1.1), Barlow Condensed(Jeremy Tribby, SIL OFL 1.1).
  라이선스 전문은 `assets/blender/fonts/OFL-*.txt`.
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
3. 올리기 전에 `npm run check`를 통과시킵니다. 모델을 고쳤다면
   `blender --background --python assets/blender/lionspark_v5_build.py`로 자산을 다시 만들고
   `assets/blender/v5-manifest.json`도 함께 커밋합니다.
4. PR에는 **무엇을, 왜, 어떻게 확인했는지**를 적습니다. 스크린샷이 있으면 더 좋습니다.

자세한 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md)에 있습니다.

## 알려 둘 것

- 이 프로젝트는 **삼성 라이온즈 구단과 무관한 비공식 팬 프로젝트**입니다. 구단의 승인·후원을
  받지 않았습니다.
- 경기장과 일대는 제공된 항공 사진·평면도·야간 외벽 사진과 공개된 규모를 토대로 한
  **해석적 재구성**입니다. 실측 도면 기반의 측량적 디지털 트윈이 아니며, 치수·동선·주변
  배치는 실제와 다를 수 있습니다.
- 응원가 음원과 구단 로고는 팬 프로젝트 시연 목적의 사용입니다. 권리자의 요청이 있으면
  해당 자산을 제거합니다.
- 이 저장소에는 개인정보·대화 기록·비밀 키, 특정 개인의 클라우드 계정 설정이 들어 있지
  않습니다. 기여할 때도 넣지 마세요.

---

**GO LIONS!** 💙🤍 — 라팍에서, 그리고 브라우저에서.
