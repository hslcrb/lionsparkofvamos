# 배포 가이드 · Deployment Guide

라팍 오브 바모스는 **개인 계정·도메인·인증서에 묶이지 않는** 오픈소스 패키지입니다.
빌드 결과물은 `out/` 하나이고, 실시간 응원은 선택 사항입니다. 아래 여섯 가지 경로 중
편한 것을 고르면 됩니다.

| 호스트 | 3D 라팍월드 | 실시간 응원 | 1분 배포 |
| --- | --- | --- | --- |
| **Docker / docker compose** | ✅ | ✅ 내장 Node 서버 | ✅ |
| **Node.js 서버(VPS·NAS·Railway·Fly.io)** | ✅ | ✅ 내장 Node 서버 | ✅ |
| **Cloudflare Workers**(본인 계정) | ✅ | ✅ Durable Object | ✅ |
| **Vercel** | ✅ | ⚠️ 실시간 없음(로컬 응원만) | ✅ |
| **Cloudflare Pages / Netlify / S3** | ✅ | ⚠️ 실시간 없음(로컬 응원만) | ✅ |
| **GitHub Pages** | ✅ | ⚠️ 실시간 없음(로컬 응원만) | ✅ |

> 실시간 응원(`/main`의 응원 수·춤 공유)은 WebSocket 서버가 필요합니다. 정적 호스트에서는
> 응원 버튼과 춤은 **내 화면에서 그대로 동작**하고, 접속자 수·누적 응원 수만 표시되지 않습니다.
> WebSocket이 없어도 페이지는 3초마다 재연결을 시도할 뿐 오류를 내지 않습니다.

---

## 0. 공통 준비

```sh
git clone https://github.com/hslcrb/lionsparkofvamos.git
cd lionsparkofvamos
npm ci          # Node.js 22 이상
npm run build   # → out/ (정적 HTML·JS·GLB·텍스처)
```

빌드 산출물:

| 파일 | 크기 | 설명 |
| --- | --- | --- |
| `out/index.html`, `out/main.html`, `out/lionspark.html`, `out/418.html` | 수십 KB | 페이지 |
| `out/_next/**` | 약 1 MB | JS·CSS |
| `out/models/lionspark.glb` | 약 8.7 MB | Draco 압축 경기장·일대 |
| `out/models/lionspark-collision.json` | 약 0.9 MB | 충돌체·출발점·야간 조명 |
| `out/models/*.jpg`, `*.png` | 약 2.5 MB | 하늘·천체 |
| `out/draco/**` | 약 0.3 MB | Draco 디코더 |

서버가 필요 없는 정적 파일이므로, 아래 어느 호스트든 **`out/` 디렉터리만** 있으면 됩니다.

---

## 1. Docker — 가장 빠른 자체 호스팅

```sh
docker compose up --build      # http://localhost:8080
```

- `Dockerfile`은 2단계입니다. 1단계에서 `npm ci && npm run build`, 2단계에는 `out/`과
  의존성 없는 Node 서버(`server/standalone.mjs`)만 들어가 최종 이미지가 가볍습니다.
- `docker-compose.yml`은 8080 포트, `cheers` 볼륨(응원 수 보존), 자동 재시작을 설정합니다.
- 포트를 바꾸려면 `PORT=3000 docker compose up --build`.
- 컨테이너 상태 확인: `curl localhost:8080/healthz` → `{"ok":true,...}`.

이미지만:

```sh
docker build -t lionspark .
docker run -p 8080:8080 -v lionspark-data:/data -e CHEERS_FILE=/data/cheers.json lionspark
```

---

## 2. Node.js 서버 · VPS · NAS

`server/standalone.mjs`는 **의존성이 없는** 정적 서버 + WebSocket 응원방입니다.
Node 22 표준 라이브러리만 쓰므로 `npm install` 없이도 돌아갑니다.

```sh
npm ci && npm run build
PORT=8080 CHEERS_FILE=/var/lib/lionspark/cheers.json npm run serve
```

| 환경 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `PORT` | `8080` | HTTP 포트 |
| `HOST` | `0.0.0.0` | 바인드 주소 |
| `CHEERS_FILE` | (없음) | 응원 수를 저장할 JSON 경로. 없으면 메모리에만 유지 |

systemd 예시:

```ini
[Unit]
Description=Lions Park of VAMOS
After=network.target

[Service]
WorkingDirectory=/srv/lionsparkofvamos
Environment=PORT=8080
Environment=CHEERS_FILE=/var/lib/lionspark/cheers.json
ExecStart=/usr/bin/node server/standalone.mjs
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

Nginx 리버스 프록시(WebSocket 업그레이드 포함):

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

> Railway, Render, Fly.io처럼 Dockerfile을 읽는 호스트는 그대로 올리면 됩니다.
> 포트는 플랫폼이 주는 `PORT` 환경 변수를 따릅니다.

---

## 3. Cloudflare Workers — 원래 구성(본인 계정)

```sh
npx wrangler login
npm run deploy        # 빌드 후 wrangler deploy
```

- `wrangler.jsonc`의 이름·Durable Object 클래스(`CheerRoom`)·마이그레이션(`v1`)은
  **그대로 두는 것을 권장**합니다. 이미 응원 수가 쌓인 방에 붙일 때 바꾸면 새 방이 됩니다.
- 계정 ID·도메인·인증서는 저장소에 들어 있지 않습니다. `wrangler login`으로 본인 계정에
  연결하면 끝입니다.
- 커스텀 도메인은 Cloudflare 대시보드에서 Worker에 붙이면 됩니다(선택).

로컬에서 배포와 같은 구성을 확인:

```sh
npm run local      # build + wrangler dev --local → http://127.0.0.1:8787
npm run verify:local
```

---

## 4. Vercel

```sh
npx vercel --prod
```

- Next.js 정적 export(`output: 'export'`)이므로 빌드 설정은 기본값 그대로 두면 됩니다.
- **실시간 응원은 동작하지 않습니다.** `/api/room` WebSocket을 Vercel 정적 배포가 받아 주지
  않기 때문입니다. 응원 버튼·춤은 로컬에서 동작하고, 접속자 수만 표시되지 않습니다.
- 실시간이 필요하면 Vercel에는 정적 페이지만 두고, Node 서버나 Worker를 별도 도메인에 올린
  뒤 리버스 프록시로 `/api/room`만 넘기는 구성을 권장합니다.

## 5. Cloudflare Pages · Netlify · S3 등 정적 호스트

| 호스트 | 빌드 명령 | 출력 디렉터리 |
| --- | --- | --- |
| Cloudflare Pages | `npm run build` | `out` |
| Netlify | `npm run build` | `out` |
| Amazon S3 + CloudFront | `npm run build` 후 `out/` 업로드 | — |

정적 호스트에서는 `/lionspark`, `/main` 같은 경로가 `lionspark.html`로 연결되도록
**clean URL 또는 `*.html` 폴백**을 켜 주세요. Cloudflare Pages는 `404.html` 폴백을 자동으로
처리하고, Netlify는 아래 한 줄이면 됩니다.

```toml
# netlify.toml
[build]
  command = "npm run build"
  publish = "out"

[[redirects]]
  from = "/main"
  to = "/main.html"
  status = 200
```

## 6. GitHub Pages

프로젝트 사이트(`https://<user>.github.io/lionsparkofvamos/`)처럼 **하위 경로**에 올릴 때는
빌드 전에 접두사를 지정합니다.

```sh
NEXT_PUBLIC_BASE_PATH=/lionsparkofvamos npm run build
touch out/.nojekyll      # _next/ 폴더가 Jekyll에 걸리지 않게
```

그 뒤 `out/`을 `gh-pages` 브랜치에 올리거나, 아래 워크플로를 사용합니다.

```yaml
name: pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: NEXT_PUBLIC_BASE_PATH="/${{ github.event.repository.name }}" npm run build
      - run: touch out/.nojekyll
      - uses: actions/upload-pages-artifact@v3
        with:
          path: out
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: github-pages
    steps:
      - uses: actions/deploy-pages@v4
```

사용자 사이트(`https://<user>.github.io/`)나 커스텀 도메인이면 `NEXT_PUBLIC_BASE_PATH` 없이
빌드하면 됩니다. `basePath`는 `next.config.ts`가 `NEXT_PUBLIC_BASE_PATH`를 읽어 적용하고,
3D 모델·음원·Draco 경로도 `src/asset-path.ts`를 통해 같은 접두사를 따릅니다.

GitHub Pages에는 WebSocket 서버가 없으므로 실시간 응원은 동작하지 않습니다. GitHub App
권한상 `.github/workflows/`를 만들 수 없는 경우에는 위 YAML을 권한이 있는 계정으로 추가하면
됩니다(현재 저장소에는 `docs`에 예시만 두고 워크플로는 커밋하지 않았습니다).

---

## 7. 정적 Nginx

```sh
npm run build
sudo cp -r out /var/www/lionspark
sudo cp deploy/nginx.conf /etc/nginx/sites-available/lionspark
sudo ln -s /etc/nginx/sites-available/lionspark /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

`deploy/nginx.conf`에는 gzip, 장기 캐시, `/418` 상태 코드, `/main`·`/lionspark` 라우팅이
들어 있습니다. 실시간 응원이 필요하면 이 파일 대신 2번(Node 서버) + 리버스 프록시를 쓰세요.

---

## 8. 운영 메모

- **HTTPS**에서는 WebSocket이 자동으로 `wss://`로 붙습니다(`location.protocol` 기준).
  프록시에서 `Upgrade`·`Connection` 헤더를 반드시 통과시켜 주세요.
- **모델 캐시**: `lionspark.glb`는 8.7 MB입니다. 대부분의 호스트가 gzip/brotli를 자동
  적용하지만, GLB는 이미 압축(Draco)되어 있어 전송량 감소 폭은 작습니다. 장기 캐시
  (`Cache-Control: public, max-age=31536000, immutable`)를 권장합니다.
- **메모리**: Node 서버는 상주 메모리 40 MB 안팎입니다. Durable Object/Node 모두 응원 수
  하나만 저장하며 계정·쿠키·채팅 로그를 저장하지 않습니다.
- **상태 초기화**: `CHEERS_FILE`을 지우거나 `docker compose down -v`로 볼륨을 지우면
  응원 수가 0부터 다시 시작합니다.
- **버전 표기**: `/healthz`는 `{ ok, cheers, online }`을 돌려줍니다. 로드밸런서 헬스체크에
  사용하세요.

## 9. 문제 해결

| 증상 | 원인 · 해결 |
| --- | --- |
| `/lionspark`가 404 | 정적 호스트의 clean URL/폴백 설정이 꺼져 있음 → `lionspark.html` 매핑 추가 |
| 모델이 안 보임 | `out/models/lionspark.glb`가 업로드됐는지, `NEXT_PUBLIC_BASE_PATH`와 실제 경로가 같은지 확인 |
| `/api/room` 426 | WebSocket 없는 정적 호스트 → 정상. Node 서버나 Worker를 써야 실시간 동작 |
| 응원 수가 안 올라감 | 정적 호스트이거나 리버스 프록시가 `Upgrade` 헤더를 막고 있음 |
| 하위 경로에서 CSS·JS 404 | `NEXT_PUBLIC_BASE_PATH` 없이 빌드함 → 접두사를 붙여 다시 빌드 |
| Docker 빌드가 느림 | `.dockerignore`가 `node_modules`·`assets/blender`를 제외하는지 확인 |

---

## 10. 배포 체크리스트

- [ ] `npm run check` 통과 (타입·린트·포맷·테스트·빌드)
- [ ] `out/models/lionspark.glb`와 `lionspark-collision.json`이 함께 배포됨
- [ ] 하위 경로 배포라면 `NEXT_PUBLIC_BASE_PATH` 지정
- [ ] 실시간 응원을 원하면 Node 서버 또는 Cloudflare Worker 사용
- [ ] HTTPS에서 `/main` 접속 후 응원 버튼이 모두에게 반영되는지 확인
- [ ] `/418`이 실제 418, 없는 주소가 실제 404를 돌려주는지 확인
