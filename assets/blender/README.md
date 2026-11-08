# Blender 소스와 재구성 파이프라인

라팍월드의 경기장은 Blender에서 **참고 사진을 보고 다시 지은 해석적 재구성**입니다. 실측 도면을
따라 그린 측량 모델이 아니며, 사진에 가려진 부분과 주변 배치는 해석한 값입니다.

## 파일

| 파일 | 설명 |
| --- | --- |
| `lionspark_build.py` | v1. 항공 사진을 보고 처음 세운 기본 형상 |
| `lionspark_v2_build.py` | v2. 사진 기반 형상 보정과 주변 환경 |
| `lionspark_v3_build.py` | v3. 최종 형상·사인 합성·충돌체 생성·GLB 내보내기 |
| `lionspark-v3.blend` | v3 작업 파일(약 49 MB) |
| `celestial_sky_texture.py` | 야간 천체 아틀라스(4096×2048) 생성기 |
| `celestial-sky-v4.blend` | 천체 아틀라스 작업 파일 |
| `v3-manifest.json`, `v2-manifest.json`, `celestial-sky-manifest.json` | 각 단계의 크기·해시·충돌체 수 기록 |
| `references/` | 재구성에 쓴 참고 사진(항공, 평면도, 야간 외벽, 주변) |
| `textures/` | Poly Haven CC0 콘크리트 텍스처와 구단 로고 표면 |
| `facade.svg` | 외벽 사인 원본 |

## 재현 순서

1. Blender에서 `lionspark_build.py`를 실행하고 `.lemonade/lionspark.blend`를 남깁니다.
2. `lionspark_v2_build.py`를 실행해 `.lemonade/lionspark-v2.blend`를 만들고
   `assets/blender/lionspark-v2.blend`로 복사합니다.
3. `lionspark_v3_build.py`를 실행합니다. **이 스크립트는 2단계의 v2 블렌드 파일을 열어
   작업을 이어갑니다.** 저장소 용량 때문에 v1·v2 블렌드 파일은 포함되어 있지 않으므로,
   v3를 처음부터 다시 만들려면 1·2단계를 먼저 실행해야 합니다.
4. 3단계가 `public/models/lionspark.glb`, `lionspark-collision.json`,
   `lionspark-scene.json`, `lionspark-sky.jpg`와 `v3-manifest.json`을 갱신합니다.

Blender 4.x + Blender MCP 환경에서 작성되었습니다. 스크립트는 `__file__` 기준으로 저장소
루트를 찾으므로 저장소 구조를 그대로 두고 실행해야 합니다.

## 권리

`references/`의 참고 사진과 `facade.svg`, 구단 로고 표면은 원 권리자의 자료입니다. 재사용
전에 [NOTICE.md](../../NOTICE.md)를 확인해 주세요. 텍스처 일부는 Poly Haven CC0입니다.
