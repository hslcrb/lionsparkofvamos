# Blender 소스와 재구성 파이프라인

라팍월드의 경기장과 주변 일대는 Blender에서 **참고 사진과 공개된 규모를 바탕으로 다시 지은
해석적 재구성**입니다. 실측 도면을 따라 그린 측량 모델이 아니며, 사진에 가려진 부분과 주변
배치는 해석한 값입니다.

## 파일

| 파일 | 설명 |
| --- | --- |
| `lionspark_v5_build.py` | **v5. 독립 실행 파이프라인.** 경기장·광장·도로·대공원역·주차장·수림에 콘코스 내부, LED 전광판, 도로명주소 표지, 주변 지리를 더해 GLB·충돌체·씬·블렌드를 내보냄 |
| `lionspark-v5.blend` | v5 편집용 씬(약 22 MB, 텍스처 패킹) |
| `lionspark_v4_build.py` | v4. 직전 단계 파이프라인(참고·비교용) |
| `lionspark-v4.blend` | v4 편집용 씬(약 18 MB, 텍스처 패킹) |
| `lionspark_v3_build.py` | v3. v2 블렌드를 열어 형상·사인·충돌체를 마무리하던 단계 |
| `lionspark-v3.blend` | v3 작업 파일(약 49 MB) |
| `lionspark_build.py`, `lionspark_v2_build.py` | v1·v2. 최초 형상과 사진 기반 보정 |
| `celestial_sky_texture.py` | 야간 천체 아틀라스(4096×2048) 생성기 |
| `celestial-sky-v4.blend` | 천체 아틀라스 작업 파일 |
| `v5-manifest.json`, `v4-manifest.json`, `v3-manifest.json`, `v2-manifest.json`, `celestial-sky-manifest.json` | 각 단계의 크기·해시·충돌체 수 기록 |
| `fonts/` | Noto Sans KR, Barlow Condensed (SIL OFL 1.1) |
| `references/` | 참고 사진과 v5 미리보기 렌더(`aerial-sunrise/day/sunset/night.png`, `plaza-sunset.png`, `interior-concourse.png`, `scoreboard-close.png`, `dugout-close.png`) |
| `textures/` | Poly Haven CC0 콘크리트 텍스처, 구단 로고 표면, `brand-*.jpg` LED 아트워크 |
| `facade.svg` | 외벽 사인 원본 |

## v5 — 한 번에 재현하기

```sh
# 저장소 루트에서
blender --background --python assets/blender/lionspark_v5_build.py

# LED 아트워크를 원본에서 다시 합성하려면 (Pillow 필요)
python3 scripts/prepare-v5-graphics.py
```

v5 스크립트는 **어떤 .blend도 열지 않습니다.** 빈 씬에서 시작해 모든 것을 생성하므로,
저장소를 클론한 사람이 곧바로 같은 결과를 만들 수 있습니다. 다음 파일이 갱신됩니다.

- `public/models/lionspark.glb` (Draco, 약 12.0 MB)
- `public/models/lionspark-collision.json` (약 0.8 MB, 9,376개 OBB)
- `public/models/lionspark-scene.json`
- `assets/blender/lionspark-v5.blend`
- `assets/blender/v5-manifest.json`
- `assets/blender/references/{aerial-sunrise,aerial-day,aerial-sunset,aerial-night,plaza-sunset,interior-concourse,interior-concourse-lower,scoreboard-close,dugout-close}.png`

렌더를 건너뛰려면 `LSV5_RENDER=none`, 미리보기 한 장만 다시 그리려면
`LSV5_RENDER=sunset LSV5_PARTS=aerial-sunset LSV5_EXPORT=0`을 붙입니다. 자세한 옵션·좌표계·
이름 규칙·내보내기 설정은 [`../../BLENDER_GUIDE.md`](../../BLENDER_GUIDE.md)에 있습니다.

## v4 — 이전 단계

v4는 콘코스 내부, LED 전광판, 도로명주소 표지, 주변 지리가 없던 단계입니다. 비교가 필요할 때만
`blender --background --python assets/blender/lionspark_v4_build.py`로 다시 만들고, 결과는
커밋하지 마세요(`v4-manifest.json`·`lionspark.glb`를 덮어씁니다).

## v1 → v3 (역사 기록)

1. Blender에서 `lionspark_build.py`를 실행하고 `.lemonade/lionspark.blend`를 남깁니다.
2. `lionspark_v2_build.py`를 실행해 `.lemonade/lionspark-v2.blend`를 만들고
   `assets/blender/lionspark-v2.blend`로 복사합니다.
3. `lionspark_v3_build.py`를 실행합니다. **이 스크립트는 2단계의 v2 블렌드 파일을 열어
   작업을 이어갑니다.** 저장소 용량 때문에 v1·v2 블렌드 파일은 포함되어 있지 않으므로,
   v3를 처음부터 다시 만들려면 1·2단계를 먼저 실행해야 합니다.
4. 3단계가 `public/models/lionspark.glb`, `lionspark-collision.json`,
   `lionspark-scene.json`과 `v3-manifest.json`을 갱신합니다.

v3는 Blender MCP 세션에서 작성되었고, v4부터는 순수 스크립트로 재현됩니다.

## 권리

`references/`의 참고 사진과 `facade.svg`, 구단 로고 표면은 원 권리자의 자료입니다. 재사용
전에 [NOTICE.md](../../NOTICE.md)를 확인해 주세요. 텍스처 일부는 Poly Haven CC0이고,
폰트는 SIL OFL 1.1입니다.
