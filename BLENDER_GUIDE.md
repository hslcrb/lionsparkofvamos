# 블렌더 가이드 · Blender Guide

이 저장소의 경기장은 **사진과 실측 치수를 바탕으로 절차적으로 다시 지은** 해석적 모델입니다.
Blender 4.x에서 `.blend`를 열어 직접 고치거나, 파이썬 스크립트를 다시 돌려 GLB·충돌체를
재생성할 수 있습니다. 외부 애드온·Blender MCP·유료 에셋은 필요 없습니다.

---

## 1. 준비물

| 항목 | 설명 |
| --- | --- |
| Blender **4.2 LTS 이상** (4.x) | 3.x에서는 glTF Draco 내보내기 옵션 이름이 다릅니다 |
| 파이썬 | Blender에 내장된 파이썬을 그대로 사용합니다 (별도 설치 불필요) |
| GPU | 필요 없음. 미리보기 렌더는 CPU(Cycles)로도 돌아갑니다 |
| 저장 공간 | `.blend` 약 25 MB, GLB 약 14.6 MB |

저장소의 관련 파일:

```
assets/blender/
  lionspark_v6_build.py     ← v6 전체 파이프라인(독립 실행, 현재 모델)
  lionspark-v6.blend        ← v6 편집용 씬 (텍스처 패킹됨)
  lionspark_v5_build.py     ← 직전 단계(v5) 파이프라인
  lionspark_v4_build.py     ← v4 파이프라인(역사 기록, 참고용)
  lionspark-v4.blend        ← v4 편집용 씬
  fonts/                    ← 한글·디스플레이 폰트 (SIL OFL 1.1)
  textures/                 ← Poly Haven CC0 콘크리트, 로고 표면, brand-*.jpg LED 그래픽
  references/               ← 참고 사진과 v6 미리보기 렌더(하늘 네 가지 + 광장·대계단·전광판)
  v6-manifest.json          ← 크기·해시·충돌체 수·지적면적·필드 축·LED 패널 목록
assets/graphics/            ← 제공받은 삼성 라이온즈 승리 그래픽 원본
public/models/
  lionspark.glb             ← 웹이 실제로 불러오는 모델
  lionspark-collision.json  ← 충돌체·출발점·야간 조명
  lionspark-scene.json      ← 씬 설명(버전·구성·필드 축·펜스 실측)
  lionspark-cadastre.json   ← 지적 151,526.00 ㎡ 꼭짓점·표고·펜스 수치
```

---

## v6에서 달라진 점

v6는 **좌표계와 도시구조를 다시 세운** 버전입니다. 오브젝트 이름 규칙·충돌 형식은 그대로입니다.

| 항목 | v5 | v6 |
| --- | --- | --- |
| 좌표계 | +Y를 남쪽으로 두는 로컬 프레임 | **+Y = 진북**, 미터, 웹은 `(x, z, −y)` |
| 필드 축 | 남향(180°) | **동북동 67.5°** (홈플레이트 → 센터) — 3루 응원석 16시 이후 그늘 |
| 펜스 | 근사 | **99.5 / 123.4 / 122.5 m, 높이 3.6 m** |
| 스탠드 | 하부 앞단 근사 | **1·3루 베이스에서 18.3 m** 필드석 |
| 지적 | 없음 | **151,526.00 ㎡** 정팔각형 + 경계석 + 지적도판 + `lionspark-cadastre.json` |
| 표고 | 평지 | **EL45 플랫폼 / EL35 달구벌대로 / 10 m 대계단**, 남동 연호산 능선 |
| 주변 | 로컬 방위 | 달구벌대로 N, 대공원역 4·5번, 연호지 NW, 알파시티 W, 법원 N, 대구스타디움·미술관 S/SE, 야구전설로 E + P1~P3 852면 |
| 그래픽 | 2026 승리 그래픽 | **WIN OR WOW** 전광판·펜스 뮤럴, **혼연일체**, 스폰서 8종, 블레오 패밀리 |
| 렌더 | 9장 | 11장(광장·대계단·근경 에어리얼 추가) |

`LSV6_*` 환경변수를 씁니다(`LSV6_*`에서 이름만 바뀌었습니다).

## v5에서 달라진 점

v5는 v4 장면을 그대로 이어받은 **확장**입니다. 좌표계·이름 규칙·충돌 형식은 바뀌지 않았습니다.

| 추가된 것 | 만든 곳 | 이름 규칙 |
| --- | --- | --- |
| 메인 LED 월(32 × 18 m), 1·3루 띠전광판, 외야 펜스·팀스토어 배너, 파사드 엠블럼 | `build_identity()`, `build_victory_dressing()` | `Night_Sign_LED_*` + `userData.led_panel` |
| 1·2층 콘코스, 매장, 구역 안내판, 보미토리 사인, VIP 스위트, 프레스 박스 | `build_interior()` | `WalkSurface_Concourse*`, `Booth_*`, `Sign_Zone_*` |
| 덕아웃 장비(배트 걸이·헬멧함·쿨러·계단 난간), 외야 불펜 | `build_dugouts_and_bullpens()` | `Dugout_*`, `Bullpen_*` |
| 야구전설로 1 도로명판, 달구벌대로 표지, 대형 안내 게이트, 역 출구 표기 | `build_street_signs()` | `Sign_Road_*`, `Guide_Sign_*` |
| 연호지 수면, 수성알파시티 타워, 연호지구 저층 블록, 대구스타디움·미술관 원경, 동측 곡선 도로 | `build_geography()` | `Water_*`, `Distant_Urban_*` |
| 천체 셰이더용 스카이돔(웹에서 대기 산란으로 대체) | `build_sky_dome()` | `SkyDome_*` |

### 미리보기 렌더

`references/`에 하늘 네 가지와 내부 장면을 남깁니다.

| 파일 | 카메라 | 하늘 |
| --- | --- | --- |
| `aerial-sunrise.png` | 항공 | 태양 고도 5°, 동쪽 |
| `aerial-day.png` | 항공 | 한낮, 태양 56° |
| `aerial-sunset.png` | 항공 | 태양 고도 8°, 서쪽 |
| `aerial-night.png` | 항공 | 조명탑·LED 점등 |
| `plaza-sunset.png` | 광장 | 노을 |
| `interior-concourse.png` / `interior-concourse-lower.png` | 2층·1층 콘코스 | 실내 조명 |
| `scoreboard-close.png` | 전광판 정면 | 노을 |
| `dugout-close.png` | 홈 덕아웃 | 낮 |

LED 아트워크는 저장소의 `assets/graphics/` 원본에서 `python3 scripts/prepare-v6-graphics.py`로
합성합니다. `scripts/prepare-v6-graphics.py`가 WIN OR WOW·혼연일체·스폰서·마스코트·지적도판을
새로 그립니다. 텍스처를 바꾸면 이 스크립트를 다시 돌리고 v6 빌드를 재실행하세요.

---

## 2. 스크립트 실행

저장소 **루트**에서 실행합니다. 스크립트는 `__file__`을 기준으로 저장소 루트를 찾습니다.

```sh
# 전체 빌드 + 미리보기 렌더 + GLB/충돌체/블렌드 저장
blender --background --python assets/blender/lionspark_v6_build.py

# 렌더 없이 빠르게 (CI·서버에서 권장)
LSV6_RENDER=none blender --background --python assets/blender/lionspark_v6_build.py

# 미리보기 한 장만 다시 렌더 (sunrise | day | sunset | night)
LSV6_RENDER=sunset LSV6_EXPORT=0 blender --background --python assets/blender/lionspark_v6_build.py
LSV6_RENDER=all LSV6_PARTS=interior-concourse,scoreboard-close LSV6_EXPORT=0 \
  blender --background --python assets/blender/lionspark_v6_build.py
```

| 환경 변수 | 기본값 | 효과 |
| --- | --- | --- |
| `LSV6_SKIP_RENDER` | `0` | `1`이면 미리보기 렌더를 모두 건너뜁니다 |
| `LSV6_RENDER` | `all` | `all` · `none` · `sunrise` · `day` · `sunset` · `night` 중 선택 |
| `LSV6_PARTS` | (없음) | 쉼표로 고른 미리보기만 렌더(`aerial-sunset,interior-concourse` 등) |
| `LSV6_EXPORT` | `1` | `0`이면 렌더만 하고 GLB·블렌드 저장을 건너뜁니다 |
| `LSV6_RES_SCALE` / `LSV6_SAMPLE_SCALE` | `1` | 미리보기 해상도·샘플 배율(빠른 확인용) |
| `LSV6_DENOISE` | `1` | `0`이면 Cycles 디노이즈를 끕니다(조금 빠름) |

GUI에서 실행하려면 Blender의 **Scripting** 워크스페이스에서 `lionspark_v6_build.py`를 열고
**Run Script**를 누릅니다. 스크립트는 씬을 새로 만들기 때문에, 먼저 저장하지 않은 작업이
있다면 백업하세요.

빌드가 끝나면 다음이 갱신됩니다.

- `public/models/lionspark.glb` — Draco 압축 GLB
- `public/models/lionspark-collision.json` — OBB 충돌체·출발점·야간 조명
- `public/models/lionspark-scene.json` — 씬 설명
- `assets/blender/lionspark-v4.blend` — 편집용 씬(텍스처 패킹)
- `assets/blender/v4-manifest.json` — 바이트·SHA-256·충돌체 수
- `assets/blender/references/aerial-v4.png`, `plaza-v4.png`, `night-v4.png`

---

## 3. 좌표계와 단위

| 항목 | 값 |
| --- | --- |
| 단위 | 미터(m) |
| Blender +X | 동쪽 |
| Blender −Y | 북쪽 — 달구벌대로(10차선) · 대공원역 4·5번 출구 |
| Blender +Y | 남쪽 — 외야 잔디석 · 연호산 수림 |
| Blender +Z | 위쪽 |
| 웹(three.js) 좌표 | `(x, z, −y)` — glTF Y-up 변환 결과 |

즉 Blender에서 `(0, −165, 0.16)`은 웹에서 `(0, 0.16, 165)`, 곧 광장 중앙입니다.
`lionspark-collision.json`의 모든 좌표도 웹 좌표계입니다.

경기장 중심은 원점, 팔각 외곽선 `P`는 다음과 같습니다(스크립트 상단 상수).

```
(-62,-128) (62,-128) (136,-54) (136,62) (62,136) (-62,136) (-136,62) (-136,-54)
```

홈플레이트 `(0,−58)`, 중견수 펜스 `(0, 64)`, 좌우 펜스 코너 `(±70, 12)`.

---

## 4. 이름 규칙 — 웹 앱이 이름으로 찾는 것들

three.js 런타임은 오브젝트·재질 이름으로 지면·조명·차량을 구분합니다. 이름을 바꾸면
기능이 조용히 꺼질 수 있으니 아래 접두사를 유지하세요.

| 접두사 | 쓰임 |
| --- | --- |
| `WalkSurface*` | 걸을 수 있는 지면. 삼각형에서 높이를 계산합니다(광장·도로·잔디·관중석 통로 등) |
| `Seat_*` | 좌석(충돌체에서 제외, 렌더 부하를 줄이는 재질 처리) |
| `Night_Facade_Glow*` | 야간 외벽 블루 워시(재질 발광) |
| `Night_Floodlight*` | 조명탑 투광기 |
| `Night_Road_Lamps*` | 가로등·광장등(따뜻한 색) |
| `Night_Sign_LED*` | 전광판·사인 LED |
| `Driveable_Car` | 플레이어가 타고 달리는 자동차의 **루트 오브젝트**(이름 정확히 일치) |
| `Car_Contact_Shadow` | 차량 접지 그림자(반투명) |
| `Tree_*`, `Plaza_Shrubs`, `Hedge` | 수목·관목(가벼운 재질 처리) |

`Driveable_Car`는 비어(Empty) 오브젝트이고, 차체 메시들이 그 자식으로 들어 있습니다.
웹은 이 루트를 찾아 `vehicleSpawn` 위치로 옮기고 조향·가속을 적용합니다.

---

## 5. 씬 구성

`lionspark-v6.blend`에는 컬렉션 하나(`Lionspark_V6_World`)에 모든 메시가 들어 있습니다.

| 그룹 | 내용 |
| --- | --- |
| 경기장 | 팔각 2층 관중석(약 36,400석), 캔틸레버 지붕과 트러스, 외벽 개구부, 게이트 2, 덕아웃, 백스톱 |
| 그라운드 | 잔디(모잉 스트라이프), 내야 흙, 마운드·베이스·파울라인, 외야 펜스와 페어폴 |
| 전광판 | 36 m × 20.4 m LED 스크린과 철골 프레임, 후면 브랜드 월 |
| 광장 | 대계단, 매표소, 팀스토어, 황금 사자상, 안내 키오스크, 기념품·벤치·볼라드 |
| 교통 | 달구벌대로 10차선·중앙분리대·가로수·가로등·횡단보도·교통섬, 야구전설로 |
| 대공원역 | 4·5번 출구 캐노피, 계단, 역명 표지, 역 대합실 |
| 주차 | P1·P2 주차장, 주차선, 조경섬, 주차 부스, 주차 차량 |
| 조경 | 외야 잔디석·모래놀이터, 연호산 수림, 가로수, 도시 원경 |

지붕은 홈플레이트 쪽 관중석(7·0·1면 + 2·6면 일부)만 덮는 D자형입니다. 실제 라팍처럼
외야는 열려 있습니다.

---

## 6. 수정 워크플로

### 6-1. 블렌드에서 직접 고치기

1. `assets/blender/lionspark-v6.blend`를 엽니다(텍스처는 패킹되어 있습니다).
2. 오브젝트를 옮기거나 재질을 바꿉니다. **이름은 그대로 두세요.**
3. `File → Export → glTF 2.0`에서 아래 설정으로 내보냅니다.
   - Format: **glTF Binary (.glb)**
   - Include: Selected Objects (경기장 메시 + `Driveable_Car` 루트)
   - Transform: **+Y Up** 체크
   - Data → Mesh: **Apply Modifiers** 체크
   - Compression: **Draco** (level 6, position 16, normal 10, texcoord 12)
   - Animation: 해제
4. `public/models/lionspark.glb`로 저장합니다.
5. 충돌체를 갱신하려면 스크립트를 다시 돌리는 편이 안전합니다(6-3 참고).

### 6-2. 스크립트 상수만 바꾸기

치수·배치의 대부분은 스크립트 상단과 각 `build_*` 함수에 상수로 모여 있습니다.

| 상수 | 의미 |
| --- | --- |
| `P` | 팔각 외곽선 좌표 |
| `HOME`, `CF`, `LF`, `RF` | 홈플레이트·중견수·좌우 펜스 코너 |
| `SIDE_ROOF`, `SIDE_ROOF_HALF` | 지붕이 덮는 면 |
| `SIDE_TIER_TWO` | 2층 관중석이 있는 면 |
| `ROAD_Y`, `ROAD_HALF` | 달구벌대로 중심선과 폭 |
| `PLAZA`, `PLAZA_Z` | 광장 범위와 높이 |

좌석 수·층수는 `build_bowl()`의 `tiers` 리스트에서 조정합니다.

### 6-3. 충돌체까지 다시 만들기

```sh
LSV6_SKIP_RENDER=1 blender --background --python assets/blender/lionspark_v6_build.py
```

스크립트가 메시의 **연결 성분마다** OBB(회전된 직사각형)를 계산해
`lionspark-collision.json`을 다시 씁니다. 지면(`WalkSurface*`)·페인트·좌석·수관은
충돌체에서 제외됩니다.

---

## 7. 충돌체 JSON 스키마

```jsonc
{
  "boxes": [],                       // (구버전 호환) 축정렬 박스, 현재는 빈 배열
  "solids": [
    {
      "cx": 12.34, "cz": -56.78,     // 중심 (웹 좌표, m)
      "hx": 1.2, "hz": 0.4,          // 절반 크기 (m)
      "yaw": 0.785,                  // 회전 (rad)
      "minY": 0.0, "maxY": 3.4       // 높이 범위 (m)
    }
  ],
  "spawn": [0, 1.7, 165],                    // 걷기 출발점 (x, y, z)
  "overview": [320, 250, 430],               // 전체 전경 카메라 위치
  "vehicleSpawn": [-130, 0.1, 235, -1.5708], // 차량 위치 + yaw
  "nightLights": [
    { "kind": "flood", "position": [x, y, z], "target": [x, y, z] }
  ],
  "units": "meters",
  "version": "district-v6"
}
```

- `kind`는 `flood`(투광등) · `facade`(외벽 워시) · `road`(가로등) 중 하나입니다.
- 웹은 이 값으로 야간 조명을 만들고, 상위 몇 개만 실제 광원으로 씁니다(성능).
- `spawn`은 광장 중앙, `overview`는 경기장을 비스듬히 내려다보는 위치입니다.

---

## 8. GLB를 다른 엔진에서 열기

| 대상 | 방법 |
| --- | --- |
| **Three.js** | `GLTFLoader` + `DRACOLoader`(`decoderPath`를 `public/draco/`로). 저장소의 `src/features/lionspark/runtime.ts`가 그대로 예시입니다 |
| **Unity** | glTFast 또는 UnityGLTF로 `.glb` 임포트. 1 unit = 1 m, Y-up. Draco는 glTFast가 지원 |
| **Unreal Engine** | Interchange glTF 임포터(UE 5.1+)로 임포트. 스케일 100(1 m → 100 uu) 확인 |
| **Blender 재임포트** | `File → Import → glTF 2.0`. 재질·텍스처가 그대로 들어옵니다 |

공통 주의:

- 좌표는 **미터·Y-up**입니다. Z-up 엔진에서는 X축 −90° 회전이 필요합니다.
- Draco로 압축되어 있으므로, 엔진에 Draco 디코더가 없으면 Blender에서
  `Compression: None`으로 다시 내보내세요(파일이 3~5배 커집니다).
- 텍스처는 GLB 안에 패킹되어 있습니다. 외부 파일 경로에 의존하지 않습니다.

---

## 9. 재질과 텍스처

- 모든 재질은 **Principled BSDF** 하나로 구성됩니다. glTF는 이 노드만 정확히 옮깁니다.
- 잔디·아스팔트·콘크리트·보도블록·점토 텍스처는 스크립트가 numpy로 생성해 **패킹**합니다
  (`texture_array()`). 외부 이미지 파일이 없어도 재현됩니다.
- 콘크리트 일부는 `assets/blender/textures/`의 Poly Haven CC0 이미지를 씁니다.
- UV는 면 법선의 지배축 기준 평면 투영입니다(수평면은 x·y, 벽은 수평축·높이).
  재질별 타일 크기는 `material(..., uv=미터)`로 지정합니다.
- 투명 유리는 `Alpha < 1` + `surface_render_method`로 내보내져 glTF `BLEND`가 됩니다.
- 한글 사인은 `fonts/NotoSansKR.ttf`를 불러 **메시로 변환**해 넣습니다. 폰트가 없으면
  기본 폰트로 대체되며 한글은 네모로 보일 수 있습니다.

---

## 10. 성능

| 항목 | v6 값 |
| --- | --- |
| 메시 오브젝트 | 665 |
| GLB | 약 14.6 MB (Draco level 6) |
| 충돌체 | 10,403개 |
| 좌석 | 39,845석 |
| 주차 | 852면 (P1·P2·P3) |
| 지적면적 | 151,526.00 ㎡ |
| 필드 축 | 동북동 67.5° |
| LED 패널 | 60여 면(메인 월·띠전광판·펜스 뮤럴·스폰서·마스코트·지적도판) |

좌석은 팬/백 두 개의 상자로 단순화해 하나의 메시로 묶었습니다(드로콜 1회). 관중석
충돌체는 의도적으로 제외했습니다. 더 가볍게 만들려면 `build_bowl()`의 `rows`와 좌석
피치(0.63 m)를 조정하세요. 삼각형을 절반으로 줄이면 GLB도 거의 절반이 됩니다.

---

## 11. 문제 해결

| 증상 | 해결 |
| --- | --- |
| `ModuleNotFoundError: numpy` | Blender 내장 파이썬에는 numpy가 들어 있습니다. 시스템 파이썬으로 실행하지 마세요 |
| 한글이 □로 보임 | `assets/blender/fonts/NotoSansKR.ttf`가 있는지 확인 |
| GLB가 너무 큼 | Draco 압축 옵션 확인, 좌석·수목 수 줄이기, 텍스처 해상도 낮추기 |
| 렌더가 메모리 부족 | `LSV6_PARTS=aerial-sunset`처럼 한 장씩 렌더, `LSV6_RES_SCALE=0.7`로 낮추기, `LSV6_DENOISE=0` |
| 웹에서 지면을 못 밟음 | `WalkSurface` 접두사가 유지됐는지 확인 |
| 차량이 안 움직임 | `Driveable_Car` 이름과 계층(자식 메시) 확인 |
| 충돌체가 벽을 뚫음 | 스크립트로 충돌체를 다시 생성(6-3). 손으로 만든 메시는 OBB 근사입니다 |

---

## 12. 라이선스

- 모델·스크립트: 저장소의 MIT 라이선스를 따릅니다.
- 폰트: **SIL Open Font License 1.1** (`fonts/OFL-*.txt`).
- 콘크리트 텍스처: Poly Haven CC0.
- 구단 로고·사인 원본: 원 권리자에게 있으며 MIT 적용 대상이 아닙니다. 자세한 내용은
  [`NOTICE.md`](../NOTICE.md)를 확인하세요.
