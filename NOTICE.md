# NOTICE — 제3자 자산과 권리 범위

이 저장소의 **소스 코드는 MIT 라이선스**(LICENSE 참고)를 따릅니다. 소프트웨어가 아니거나
다른 권리가 걸린 자산은 아래와 같이 별도로 다룹니다. 배포·재사용 전에 각 항목의 출처를
확인해 주세요.

## 1. 구단 상표와 응원가 (MIT 라이선스 적용 대상 아님)

| 자산 | 위치 | 권리 |
| --- | --- | --- |
| 삼성 라이온즈 엠블럼/로고 | `public/lions.svg`, `public/vamos.svg`, `src/LionsLogos.tsx`, `assets/blender/textures/lions-crest-v3.png`, `assets/blender/textures/facade-logo-v3.png` | 구단 및 원 권리자. 응원 목적의 비공식 팬 프로젝트에 한해 사용합니다. |
| VAMOS 워드마크·엠블럼 | `public/vamos.svg`, `source-materials/attachments/` | 원 권리자. |
| ‘나의 라이온즈’ 응원가 음원 | `public/my-lions.mp3` | LionsTV / 삼성 라이온즈 및 원 권리자. 이 저장소는 MIT로 재배포하지 않으며, 3초 페이드 인·10% 이득 등 원 설계를 바꾸지 않습니다. |
| 경기장 외벽 사인 원본 | `대구 삼성 라이온즈 파크.svg` | 원 권리자. |
| 구장명·역명·도로명 사인 | `assets/blender/lionspark_v5_build.py`가 폰트로 생성 | 명칭 자체는 각 권리자에게 있습니다. |
| 2026 한국시리즈 승리 그래픽 | `assets/graphics/` 원본, `assets/blender/textures/brand-*.jpg` 합성본 | 프로젝트 소유자가 직접 제작해 제공한 아트워크. 전광판·띠전광판·펜스 배너에 사용합니다. 구단 상표가 포함되므로 위 구단 로고와 같은 범위로 다룹니다. |

이 저장소는 **삼성 라이온즈 구단이 운영·승인한 공식 서비스가 아닙니다.** 구단 로고·응원가를
상업적으로 사용하거나, 상표권과 별개의 상품·서비스로 오인될 수 있게 쓰지 마세요. 권리자 요청이
있으면 해당 자산은 즉시 제거됩니다.

## 2. Creative Commons 자산

| 자산 | 위치 | 라이선스 |
| --- | --- | --- |
| Kloofendal 38d Partly Cloudy Pure Sky (Greg Zaal, Jarod Guest) — 하늘 사진 | `public/models/lionspark-sky.jpg` | CC0 1.0 · https://polyhaven.com/a/kloofendal_38d_partly_cloudy_puresky |
| Concrete Pavement 03 (Charlotte Baglioni) | `assets/blender/textures/concrete_pavement_03_*` | CC0 1.0 · https://polyhaven.com/a/concrete_pavement_03 |
| Noto Sans KR (Adobe) | `assets/blender/fonts/NotoSansKR.ttf` | SIL Open Font License 1.1 · `assets/blender/fonts/OFL-NotoSansKR.txt` |
| Barlow Condensed (Jeremy Tribby) | `assets/blender/fonts/BarlowCondensed-Bold.ttf` | SIL Open Font License 1.1 · `assets/blender/fonts/OFL-BarlowCondensed.txt` |

## 3. 소스가 공개된 외부 구현

- **three.js Sky (Preetham 대기 산란 모델)** — MIT · https://threejs.org/docs/pages/Sky.html
- **NOAA / Meeus 태양 위치·일출·일몰 근사식** — 문서·공식 참고 · https://gml.noaa.gov/grad/solcalc/calcdetails.html
- **Astropy Galactic 좌표계 (은하 극 방향 참고)** — BSD-3-Clause · https://github.com/astropy/astropy/blob/main/astropy/coordinates/builtin_frames/galactic.py
- **Draco 디코더** — Apache License 2.0 · `public/draco/LICENSE.txt`, `public/draco/SOURCE.txt`

## 4. 이 저장소에서 직접 만든 자산

- 경기장·일대 메시와 충돌 데이터: `assets/blender/lionspark-v5.blend`,
  `assets/blender/lionspark_v5_build.py`, `public/models/lionspark.glb`,
  `public/models/lionspark-collision.json` (이전 단계: `lionspark-v4.blend`, `lionspark_v4_build.py`)
- 절차적 텍스처(잔디·점토·아스팔트·보도블록·지붕): `lionspark_v5_build.py`의 `texture_array()`가
  numpy로 생성하며 별도 이미지 파일에 의존하지 않습니다.
- 천체 대기 시뮬레이션: `assets/blender/celestial_sky_texture.py`, `assets/blender/celestial-sky-v4.blend`,
  `public/models/celestial-night.png`

경기장은 제공된 항공 사진·평면도·야간 외벽 사진을 토대로 Blender에서 다시 지은 **해석적 재구성**
입니다. 실측 도면 기반의 측량적 디지털 트윈이 아니며, 치수·동선·주변 배치는 실제와 다를 수
있습니다.
