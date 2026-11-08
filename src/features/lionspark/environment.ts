import * as THREE from 'three';
import type { NightLightAnchor } from './navigation';
import { previewEpochAtElevation, sampleCelestial } from './astronomy';
import { createCelestialSky } from './celestial-sky';

export type ParkTimeMode = 'live' | 'sunrise' | 'day' | 'sunset' | 'night';

/** Golden-hour previews deliberately sit above the horizon, as the brief asks. */
export const PREVIEW_SUN_ELEVATIONS = { sunrise: 5, sunset: 8 } as const;

const DAY_MS = 86_400_000;
const KOREA_OFFSET_MS = 9 * 3_600_000;

export function getSeoulSeconds(epochMs: number): number {
    return ((((epochMs + KOREA_OFFSET_MS) % DAY_MS) + DAY_MS) % DAY_MS) / 1000;
}

export function formatSeoulTime(epochMs: number): string {
    const seconds = Math.floor(getSeoulSeconds(epochMs));
    return [Math.floor(seconds / 3600), Math.floor((seconds % 3600) / 60), seconds % 60]
        .map((value) => String(value).padStart(2, '0'))
        .join(':');
}

export function createParkClock(now: () => number = Date.now) {
    let mode: ParkTimeMode = 'live';
    let offset = 0;
    return {
        setMode(next: ParkTimeMode) {
            mode = next;
            const current = now();
            offset =
                next === 'live'
                    ? 0
                    : next === 'sunrise' || next === 'sunset'
                      ? previewEpochAtElevation(current, next, PREVIEW_SUN_ELEVATIONS[next]) -
                        current
                      : (next === 'day' ? 14 : 21) * 3_600_000 - getSeoulSeconds(current) * 1000;
        },
        read() {
            const epochMs = now() + offset;
            return { epochMs, timeMode: mode, timeLabel: formatSeoulTime(epochMs) };
        },
    };
}

export function sampleParkLighting(epochMs: number) {
    const celestial = sampleCelestial(epochMs);
    const elevation = celestial.sunDirection.y;
    const daylight = THREE.MathUtils.smoothstep(celestial.sunAltitudeRadians, -0.14, 0.1);
    const night = 1 - daylight;
    return {
        night,
        sunIntensity: Math.max(0, elevation) ** 0.55 * 2.4,
        hemisphereIntensity: 0.48 + daylight * 1.12,
        exposure: 1.12 - daylight * 0.07,
        sunDirection: celestial.sunDirection,
    };
}

type SurfaceMaterial = THREE.Material & {
    fog?: boolean;
    color?: THREE.Color;
    emissive?: THREE.Color;
    emissiveIntensity?: number;
    map?: THREE.Texture | null;
    emissiveMap?: THREE.Texture | null;
};

function surfaceNames(object: THREE.Object3D): string {
    const names: string[] = [];
    for (let current: THREE.Object3D | null = object; current; current = current.parent) {
        names.push(current.name);
    }
    return names.join(' ').toLowerCase();
}

function isSkyDome(object: THREE.Object3D): boolean {
    for (let current: THREE.Object3D | null = object; current; current = current.parent) {
        if (current.name.toLowerCase().startsWith('skydome')) return true;
    }
    return false;
}

function diffuseSceneryMaterial(original: THREE.MeshStandardMaterial) {
    return new THREE.MeshLambertMaterial({
        name: original.name,
        color: original.color,
        map: original.map,
        alphaMap: original.alphaMap,
        normalMap: original.normalMap,
        normalMapType: original.normalMapType,
        normalScale: original.normalScale,
        bumpMap: original.bumpMap,
        bumpScale: original.bumpScale,
        aoMap: original.aoMap,
        aoMapIntensity: original.aoMapIntensity,
        lightMap: original.lightMap,
        lightMapIntensity: original.lightMapIntensity,
        emissive: original.emissive,
        emissiveMap: original.emissiveMap,
        emissiveIntensity: original.emissiveIntensity,
        transparent: original.transparent,
        opacity: original.opacity,
        alphaTest: original.alphaTest,
        side: original.side,
        vertexColors: original.vertexColors,
        depthTest: original.depthTest,
        depthWrite: original.depthWrite,
        polygonOffset: original.polygonOffset,
        polygonOffsetFactor: original.polygonOffsetFactor,
        polygonOffsetUnits: original.polygonOffsetUnits,
        wireframe: original.wireframe,
        fog: original.fog,
    });
}

export function createParkEnvironment(
    scene: THREE.Scene,
    renderer: THREE.WebGLRenderer,
    coarse: boolean,
) {
    const background = new THREE.Color();
    scene.background = background;
    const daySky = new THREE.Color(0xbddff0);
    const nightSky = new THREE.Color(0x071125);
    const hemisphere = new THREE.HemisphereLight(0xe3f5ff, 0x81936c, 1.6);
    const sun = new THREE.DirectionalLight(0xfff3df, 2.4);
    sun.castShadow = true;
    sun.shadow.mapSize.set(coarse ? 1024 : 2048, coarse ? 1024 : 2048);
    Object.assign(sun.shadow.camera, {
        left: -240,
        right: 240,
        top: 240,
        bottom: -240,
        near: 1,
        far: 850,
    });
    sun.shadow.bias = -0.00015;
    sun.shadow.normalBias = 0.15;
    scene.add(hemisphere, sun, sun.target);
    const skies: ReturnType<typeof createCelestialSky>[] = [];
    const cloudTextures = new Set<THREE.Texture>();
    let nightTexture: THREE.Texture | null = null;
    let disposed = false;
    const glowMaterials: { material: SurfaceMaterial; strength: number }[] = [];
    const ledMaterials = new Map<THREE.Material, number>();
    const replacedMaterials = new Set<THREE.Material>();
    const extraLights: { light: THREE.PointLight | THREE.SpotLight; strength: number }[] = [];
    const roadAnchors: NightLightAnchor[] = [];
    const roadLights: THREE.PointLight[] = [];
    let lastUpdate = -Infinity;
    let lastShadowUpdate = -Infinity;

    function prepareModel(model: THREE.Object3D, anchors: readonly NightLightAnchor[] = []) {
        const cache = new Map<string, SurfaceMaterial>();
        let car: THREE.Object3D | undefined;
        model.traverse((object) => {
            if (/^Driveable_Car(?:[._]\d+)?$/i.test(object.name)) car = object;
            if (!(object instanceof THREE.Mesh)) return;
            if (object.userData.led_panel === true) {
                // LED walls, ribbon boards and banners keep the artwork's own
                // emission; the scene only scales it with the time of day.
                object.castShadow = false;
                object.receiveShadow = false;
                const panels = Array.isArray(object.material) ? object.material : [object.material];
                for (const panel of panels) {
                    const surface = panel as SurfaceMaterial;
                    surface.fog = false;
                    if (!ledMaterials.has(panel))
                        ledMaterials.set(panel, surface.emissiveIntensity ?? 1);
                }
                return;
            }
            const names = surfaceNames(object);
            const sky = isSkyDome(object);
            if (sky) {
                const originals = Array.isArray(object.material)
                    ? object.material
                    : [object.material];
                const original = originals[0] as SurfaceMaterial | undefined;
                const cloudMap = original?.map ?? original?.emissiveMap ?? null;
                if (cloudMap) cloudTextures.add(cloudMap);
                for (const material of originals) replacedMaterials.add(material);
                const celestialSky = createCelestialSky(object, cloudMap, nightTexture);
                skies.push(celestialSky);
                object.material = celestialSky.material;
                return;
            }
            const apply = (original: SurfaceMaterial): SurfaceMaterial => {
                const materialNames = `${names} ${original.name.toLowerCase()}`;
                const facade = /night_facade_glow/.test(materialNames);
                const flood = /night_floodlight/.test(materialNames);
                const road = /night_road_lamps/.test(materialNames);
                const contactShadow = /car_contact_shadow/.test(materialNames);
                const stableLogo = object.userData.stable_logo === true;
                const sign =
                    stableLogo ||
                    /facade_luminous_logo|original.*(?:svg|sign)|(?:svg|sign).*original/.test(
                        materialNames,
                    );
                const plain =
                    original instanceof THREE.MeshStandardMaterial &&
                    /seat_|parked_cars|tree_|woodland_|plaza_shrubs|planting|walksurface|field_|infield|mound|planter_soil|paving|distant_urban/.test(
                        materialNames,
                    ) &&
                    !/driveable_car|sky|night_|logo|svg|glass|window|roof|steel|metal|water/.test(
                        materialNames,
                    );
                if (!sky && !facade && !flood && !road && !sign && !plain && !contactShadow)
                    return original;
                if (!plain) {
                    object.castShadow = false;
                    object.receiveShadow = false;
                }
                const role = sky
                    ? 'sky'
                    : facade
                      ? 'facade'
                      : flood
                        ? 'flood'
                        : road
                          ? 'road'
                          : stableLogo
                            ? 'logo'
                            : sign
                              ? 'sign'
                              : contactShadow
                                ? 'shadow'
                                : 'plain';
                const key = `${original.uuid}:${role}`;
                const cached = cache.get(key);
                if (cached) return cached;
                const material = (
                    plain && original instanceof THREE.MeshStandardMaterial
                        ? diffuseSceneryMaterial(original)
                        : original.clone()
                ) as SurfaceMaterial;
                replacedMaterials.add(original);
                cache.set(key, material);
                if (!plain && !contactShadow && material.emissive) {
                    if (facade) material.emissive.set(0x167aff);
                    else if (flood) material.emissive.set(0xffffff);
                    else if (road)
                        material.emissive.set(
                            materialNames.includes('car_headlamp') ? 0xf2f6ff : 0xffe4be,
                        );
                    else {
                        material.emissive.copy(material.color ?? new THREE.Color(0xffffff));
                        if (material.map) material.emissiveMap = material.map;
                    }
                    glowMaterials.push({
                        material,
                        strength: facade ? 2.2 : flood ? 3 : road ? 1.9 : 1.2,
                    });
                }
                if (sign) {
                    material.polygonOffset = true;
                    material.polygonOffsetFactor = -1;
                    material.polygonOffsetUnits = -1;
                    if (stableLogo && material.transparent) {
                        material.alphaTest = Math.max(0.35, material.alphaTest);
                        material.depthWrite = true;
                    }
                }
                if (contactShadow) {
                    material.transparent = true;
                    material.depthWrite = false;
                    material.polygonOffset = true;
                    material.polygonOffsetFactor = -1;
                    material.polygonOffsetUnits = -1;
                }
                return material;
            };
            object.material = Array.isArray(object.material)
                ? object.material.map(apply)
                : apply(object.material);
        });
        if (car) {
            for (const side of [-0.52, 0.52]) {
                const light = new THREE.SpotLight(0xf2f6ff, 0, 42, Math.PI / 6.1, 0.45, 1.5);
                light.name = 'Vehicle_Headlight';
                light.position.set(side, 0.7, -2.1);
                light.target.position.set(Math.sign(side) * 0.5, 0, -25);
                car.add(light, light.target);
                extraLights.push({ light, strength: 3200 });
            }
        }
        roadAnchors.push(...anchors.filter((anchor) => anchor.kind === 'road'));
        for (const anchor of roadAnchors.slice(0, 4)) {
            const light = new THREE.PointLight(0xffe6c7, 0, 48, 1.5);
            light.name = 'Night_Road_Light_Pool';
            light.position.fromArray(anchor.position);
            scene.add(light);
            roadLights.push(light);
            extraLights.push({ light, strength: 1800 });
        }
        const counts = { flood: 0, facade: 0 };
        for (const anchor of anchors) {
            if (anchor.kind === 'road') continue;
            if (counts[anchor.kind] >= (anchor.kind === 'facade' ? 2 : 4)) continue;
            counts[anchor.kind] += 1;
            const flood = anchor.kind === 'flood';
            const strength = flood ? 14_000 : 1500;
            const light = flood
                ? new THREE.SpotLight(0xf1f5ff, 0, 170, Math.PI / 3.1, 0.65, 1.5)
                : new THREE.PointLight(0x126bff, 0, 45, 1.5);
            light.position.fromArray(anchor.position);
            if (light instanceof THREE.SpotLight) {
                light.target.position.fromArray(anchor.target);
                scene.add(light.target);
            }
            scene.add(light);
            extraLights.push({ light, strength });
        }
    }

    function update(epochMs: number, force = false, observer?: { x: number; z: number }) {
        if (!force && Math.abs(epochMs - lastUpdate) < 1000) return;
        for (const sky of skies) sky.update(epochMs);
        lastUpdate = epochMs;
        const sample = sampleParkLighting(epochMs);
        background.copy(daySky).lerp(nightSky, sample.night);
        if (observer && roadLights.length) {
            const distance = (anchor: NightLightAnchor) =>
                (anchor.position[0] - observer.x) ** 2 + (anchor.position[2] - observer.z) ** 2;
            const nearby = roadAnchors.slice().sort((a, b) => distance(a) - distance(b));
            roadLights.forEach((light, index) => {
                const anchor = nearby[index];
                if (anchor) light.position.fromArray(anchor.position);
            });
        }
        for (const { material, strength } of glowMaterials) {
            material.emissiveIntensity = sample.night * strength;
        }
        for (const [material, base] of ledMaterials) {
            const surface = material as SurfaceMaterial;
            surface.emissiveIntensity = base * (0.55 + 0.65 * sample.night);
        }
        for (const { light, strength } of extraLights) light.intensity = sample.night * strength;
        hemisphere.intensity = sample.hemisphereIntensity;
        hemisphere.color.set(0xe3f5ff).lerp(new THREE.Color(0x829ec9), sample.night);
        hemisphere.groundColor.set(0x81936c).lerp(new THREE.Color(0x263349), sample.night);
        sun.intensity = sample.sunIntensity;
        sun.color
            .set(0xfff3df)
            .lerp(new THREE.Color(0xffb46d), 1 - Math.min(1, sample.sunDirection.y * 3));
        sun.position.set(
            sample.sunDirection.x * 330,
            sample.sunDirection.y * 330,
            sample.sunDirection.z * 330,
        );
        renderer.toneMappingExposure = sample.exposure;
        if (force || Math.abs(epochMs - lastShadowUpdate) >= 30_000) {
            lastShadowUpdate = epochMs;
            renderer.shadowMap.needsUpdate = true;
        }
    }

    return {
        prepareModel,
        setSkyTexture(texture: THREE.Texture) {
            if (disposed) {
                texture.dispose();
                return;
            }
            if (nightTexture && nightTexture !== texture) nightTexture.dispose();
            nightTexture = texture;
            for (const sky of skies) sky.setNightMap(texture);
        },
        animate(epochMs: number, camera: THREE.Camera) {
            // Sky projection uses only view rotation, so walking and driving create no parallax.
            if (!camera.isCamera) return;
            for (const sky of skies) sky.update(epochMs);
        },
        update,
        dispose() {
            if (disposed) return;
            disposed = true;
            nightTexture?.dispose();
            for (const texture of cloudTextures) texture.dispose();
            for (const sky of skies) sky.material.dispose();
            for (const original of replacedMaterials) original.dispose();
            sun.shadow.dispose();
            scene.remove(hemisphere, sun, sun.target);
            for (const { light } of extraLights) {
                light.removeFromParent();
                if (light instanceof THREE.SpotLight) light.target.removeFromParent();
                light.dispose();
            }
        },
    };
}
