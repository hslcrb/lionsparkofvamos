import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import type { NightLightAnchor } from '../src/features/lionspark/navigation';
import {
    createParkClock,
    createParkEnvironment,
    formatSeoulTime,
    getSeoulSeconds,
    sampleParkLighting,
} from '../src/features/lionspark/environment';

test('Korean clock crosses midnight at 15:00 UTC and ignores browser timezone', () => {
    const before = Date.parse('2026-11-03T14:59:59Z');
    assert.equal(formatSeoulTime(before), '23:59:59');
    assert.equal(formatSeoulTime(before + 1000), '00:00:00');
    assert.equal(getSeoulSeconds(Date.parse('2026-11-03T00:00:00Z')), 9 * 3600);
});

test('car lamps follow night mode after detaching, and headlights are disposed with their targets', () => {
    const scene = new THREE.Scene();
    const renderer = { shadowMap: { needsUpdate: false } } as THREE.WebGLRenderer;
    const environment = createParkEnvironment(scene, renderer, false);
    const model = new THREE.Group();
    const car = new THREE.Group();
    car.name = 'Driveable_Car';
    const material = new THREE.MeshStandardMaterial({ color: 0xffffff });
    const lamp = new THREE.Mesh(new THREE.BufferGeometry(), material);
    lamp.name = 'Night_Road_Lamps_Car_Headlamps';
    car.add(lamp);
    model.add(car);
    scene.add(model);
    environment.prepareModel(model);
    scene.attach(car);
    const headlights = car.children.filter(
        (object): object is THREE.SpotLight => object instanceof THREE.SpotLight,
    );
    assert.equal(headlights.length, 2);
    for (const light of headlights) {
        assert.equal(light.castShadow, false);
        assert.equal(light.target.parent, car);
        assert.equal(light.position.z, -2.1);
        assert.equal(light.target.position.z, -25);
    }
    environment.update(Date.parse('2026-11-03T21:00:00+09:00'), true);
    assert.ok((lamp.material as THREE.MeshStandardMaterial).emissiveIntensity > 1);
    assert.ok(headlights.every((light) => light.intensity > 1000 && light.distance >= 35));
    environment.update(Date.parse('2026-11-03T14:00:00+09:00'), true);
    assert.ok(headlights.every((light) => light.intensity === 0));
    assert.equal(material.emissive.getHex(), 0);
    let disposed = 0;
    for (const light of headlights)
        light.addEventListener('dispose', () => {
            disposed += 1;
        });
    environment.dispose();
    assert.equal(disposed, 2);
    assert.ok(headlights.every((light) => !light.parent && !light.target.parent));
    lamp.geometry.dispose();
    (lamp.material as THREE.Material).dispose();
});

test('stable transparent logos retain their texture and color without casting rectangular shadows', () => {
    const scene = new THREE.Scene();
    const renderer = { shadowMap: { needsUpdate: false } } as THREE.WebGLRenderer;
    const environment = createParkEnvironment(scene, renderer, false);
    const texture = new THREE.Texture();
    const material = new THREE.MeshStandardMaterial({
        color: 0x1234ab,
        map: texture,
        transparent: true,
    });
    const logo = new THREE.Mesh(new THREE.BufferGeometry(), material);
    logo.userData.stable_logo = true;
    logo.castShadow = true;
    logo.receiveShadow = true;
    scene.add(logo);
    environment.prepareModel(scene);
    const prepared = logo.material as THREE.MeshStandardMaterial;
    assert.equal(logo.castShadow, false);
    assert.equal(logo.receiveShadow, false);
    assert.equal(prepared.map, texture);
    assert.equal(prepared.color.getHex(), material.color.getHex());
    assert.ok(prepared.alphaTest >= 0.35);
    assert.equal(prepared.depthWrite, true);
    assert.equal(material.alphaTest, 0);
    environment.dispose();
    prepared.dispose();
    texture.dispose();
    logo.geometry.dispose();
});

test('live clock follows the actual epoch, including time spent in a hidden tab', () => {
    let now = Date.parse('2026-11-03T01:20:00Z');
    const clock = createParkClock(() => now);
    assert.equal(clock.read().timeLabel, '10:20:00');
    now += 91_000;
    assert.equal(clock.read().timeLabel, '10:21:31');
    assert.equal(clock.read().epochMs, now);
});

test('day and night previews advance continuously and live restores the real clock', () => {
    let now = Date.parse('2026-11-03T01:20:00Z');
    const clock = createParkClock(() => now);
    clock.setMode('night');
    assert.equal(clock.read().timeLabel, '21:00:00');
    now += 1250;
    assert.equal(clock.read().timeLabel, '21:00:01');
    assert.equal(clock.read().epochMs % 1000, 250);
    clock.setMode('day');
    assert.equal(clock.read().timeLabel, '14:00:00');
    now += 2000;
    assert.equal(clock.read().timeLabel, '14:00:02');
    clock.setMode('live');
    assert.equal(clock.read().epochMs, now);
    assert.equal(clock.read().timeLabel, '10:20:03');
});

test('lighting transitions continuously at dawn, dusk, and Korean midnight', () => {
    const at = (time: string) => sampleParkLighting(Date.parse(`2026-11-03T${time}+09:00`));
    assert.ok(at('14:00:00').sunIntensity > at('21:00:00').sunIntensity);
    assert.ok(at('21:00:00').night > 0.99);
    assert.ok(at('14:00:00').night < 0.01);
    for (const time of ['06:00:00', '18:00:00', '00:00:00']) {
        const epoch = Date.parse(`2026-11-03T${time}+09:00`);
        const before = sampleParkLighting(epoch - 1000);
        const after = sampleParkLighting(epoch + 1000);
        assert.ok(Math.abs(before.night - after.night) < 0.002);
        assert.ok(Math.abs(before.sunIntensity - after.sunIntensity) < 0.002);
    }
    const before = at('23:59:59');
    const after = sampleParkLighting(Date.parse('2026-11-04T00:00:01+09:00'));
    assert.ok(Math.abs(before.sunDirection.x - after.sunDirection.x) < 0.001);
    assert.ok(Math.abs(before.sunDirection.y - after.sunDirection.y) < 0.001);
});

test('the Blender sky geometry carries scattering, stars and camera independent celestial motion', () => {
    const scene = new THREE.Scene();
    const renderer = { shadowMap: { needsUpdate: false } } as THREE.WebGLRenderer;
    const environment = createParkEnvironment(scene, renderer, false);
    const cloudTexture = new THREE.Texture();
    const nightTexture = new THREE.Texture();
    const original = new THREE.MeshBasicMaterial({ color: 0xffffff, map: cloudTexture });
    const geometry = new THREE.BufferGeometry();
    const sky = new THREE.Mesh<THREE.BufferGeometry, THREE.Material>(geometry, original);
    sky.name = 'SkyDome_Photographic_Environment.001';
    scene.add(sky);
    environment.setSkyTexture(nightTexture);
    environment.prepareModel(scene);
    const material = sky.material as THREE.ShaderMaterial;
    assert.ok(material instanceof THREE.ShaderMaterial);
    assert.equal(sky.geometry, geometry);
    assert.equal(material.uniforms.uNightMap?.value, nightTexture);
    assert.equal(material.uniforms.uCloudMap?.value, cloudTexture);
    environment.update(Date.parse('2026-11-03T21:00:00+09:00'), true);
    assert.ok(material.uniforms.uNightVisibility?.value > 0.99);
    assert.equal(material.transparent, false);
    assert.equal(material.depthWrite, false);
    assert.equal(sky.castShadow, false);
    assert.equal(sky.receiveShadow, false);
    assert.equal(sky.frustumCulled, false);
    assert.equal(sky.renderOrder, -1000);
    const epoch = Date.parse('2026-11-03T21:00:00+09:00');
    environment.animate(epoch, new THREE.PerspectiveCamera());
    const time = material.uniforms.uAnimationTime?.value;
    const basis = (material.uniforms.uRa0?.value as THREE.Vector3).clone();
    environment.animate(epoch + 33, new THREE.PerspectiveCamera());
    assert.notEqual(material.uniforms.uAnimationTime?.value, time);
    environment.animate(epoch + 3_600_000, new THREE.PerspectiveCamera());
    assert.ok(basis.distanceTo(material.uniforms.uRa0?.value as THREE.Vector3) > 0.1);
    environment.update(Date.parse('2026-11-03T14:00:00+09:00'), true);
    assert.equal(material.uniforms.uNightVisibility?.value, 0);
    assert.equal(original.opacity, 1);
    let textureDisposals = 0;
    nightTexture.addEventListener('dispose', () => textureDisposals++);
    environment.dispose();
    assert.equal(textureDisposals, 1);
    material.dispose();
    geometry.dispose();
    cloudTexture.dispose();
});

test('sunrise and sunset previews track this Korean date and keep advancing', () => {
    let now = Date.parse('2026-11-03T01:20:00Z');
    const clock = createParkClock(() => now);
    clock.setMode('sunrise');
    const sunrise = clock.read();
    assert.ok(sunrise.timeLabel >= '06:50:00' && sunrise.timeLabel < '07:15:00');
    assert.ok(Math.abs(sampleParkLighting(sunrise.epochMs).sunDirection.y) < 0.015);
    now += 1500;
    assert.equal(clock.read().epochMs, sunrise.epochMs + 1500);
    clock.setMode('sunset');
    const sunset = clock.read();
    assert.ok(sunset.timeLabel >= '17:10:00' && sunset.timeLabel < '17:40:00');
    assert.ok(Math.abs(sampleParkLighting(sunset.epochMs).sunDirection.y) < 0.015);
    clock.setMode('live');
    assert.equal(clock.read().epochMs, now);
});

test('roof skylight panes retain their original surface instead of becoming a sky dome', () => {
    const scene = new THREE.Scene();
    const renderer = { shadowMap: { needsUpdate: false } } as THREE.WebGLRenderer;
    const environment = createParkEnvironment(scene, renderer, false);
    const geometry = new THREE.BufferGeometry();
    const material = new THREE.MeshStandardMaterial({ color: 0x71818d, transparent: true });
    const pane = new THREE.Mesh(geometry, material);
    pane.name = 'Annex_Roof_Skylights_Glass';
    pane.castShadow = true;
    scene.add(pane);
    environment.prepareModel(scene);
    assert.equal(pane.geometry, geometry);
    assert.equal(pane.material, material);
    assert.equal(pane.renderOrder, 0);
    assert.equal(pane.frustumCulled, true);
    assert.equal(pane.castShadow, true);
    environment.dispose();
    material.dispose();
    geometry.dispose();
});

test('Blender emissive sky photographs remain cloud sources and shared textures dispose once', () => {
    const scene = new THREE.Scene();
    const renderer = { shadowMap: { needsUpdate: false } } as THREE.WebGLRenderer;
    const environment = createParkEnvironment(scene, renderer, false);
    const photograph = new THREE.Texture();
    const original = new THREE.MeshStandardMaterial({ emissiveMap: photograph });
    const dome = new THREE.Group();
    dome.name = 'SkyDome_Photographic_Environment';
    const sky = new THREE.Mesh<THREE.BufferGeometry, THREE.Material>(
        new THREE.BufferGeometry(),
        original,
    );
    dome.add(sky, sky.clone());
    scene.add(dome);
    environment.prepareModel(scene);
    const material = sky.material as THREE.ShaderMaterial;
    assert.equal(material.uniforms.uCloudMap?.value, photograph);
    assert.equal(material.uniforms.uHasCloudMap?.value, 1);
    const utcMidnight = Date.parse('2026-11-04T00:00:00Z');
    const cloudWrap = (Math.ceil((utcMidnight / 1000) * 0.000003) / 0.000003) * 1000;
    for (const seam of [utcMidnight, cloudWrap]) {
        environment.animate(seam - 100, new THREE.PerspectiveCamera());
        const before = material.uniforms.uCloudPhase?.value as number;
        environment.animate(seam + 100, new THREE.PerspectiveCamera());
        const after = material.uniforms.uCloudPhase?.value as number;
        const continuousDelta = ((((after - before + 0.5) % 1) + 1) % 1) - 0.5;
        assert.ok(Math.abs(continuousDelta - 0.2 * 0.000003) < 1e-9);
    }
    let disposals = 0;
    photograph.addEventListener('dispose', () => disposals++);
    environment.dispose();
    environment.dispose();
    assert.equal(disposals, 1);
    sky.geometry.dispose();
});

test('four road lights follow nearby fixture anchors without increasing the GPU light count', () => {
    const scene = new THREE.Scene();
    const renderer = { shadowMap: { needsUpdate: false } } as THREE.WebGLRenderer;
    const environment = createParkEnvironment(scene, renderer, false);
    const anchors: NightLightAnchor[] = Array.from({ length: 11 }, (_, index) => ({
        kind: 'road',
        position: [index * 10, 6.5, 0],
        target: [index * 10, 0, 0],
    }));
    environment.prepareModel(scene, anchors);
    const lights = scene.children.filter(
        (object): object is THREE.PointLight => object instanceof THREE.PointLight,
    );
    assert.equal(lights.length, 4);
    const night = Date.parse('2026-11-03T21:00:00+09:00');
    environment.update(night, true, { x: 0, z: 0 });
    assert.deepEqual(
        lights.map((light) => light.position.x).sort((a, b) => a - b),
        [0, 10, 20, 30],
    );
    assert.ok(lights.every((light) => light.intensity >= 1500 && light.distance >= 40));
    environment.update(night + 1000, false, { x: 100, z: 0 });
    assert.deepEqual(
        lights.map((light) => light.position.x).sort((a, b) => a - b),
        [70, 80, 90, 100],
    );
    assert.equal(scene.children.filter((object) => object instanceof THREE.PointLight).length, 4);
    environment.dispose();
    assert.ok(lights.every((light) => !light.parent));
});

test('dense diffuse scenery keeps its maps and colors while the driven car retains glossy material', () => {
    const scene = new THREE.Scene();
    const renderer = { shadowMap: { needsUpdate: false } } as THREE.WebGLRenderer;
    const environment = createParkEnvironment(scene, renderer, false);
    const texture = new THREE.Texture();
    const normalMap = new THREE.Texture();
    const original = new THREE.MeshStandardMaterial({
        color: 0x7d8a95,
        map: texture,
        normalMap,
        roughness: 0.3,
    });
    const pavement = new THREE.Mesh(new THREE.BufferGeometry(), original);
    pavement.name = 'WalkSurface_Entrance_Plaza';
    pavement.receiveShadow = true;
    const car = new THREE.Group();
    car.name = 'Driveable_Car';
    const body = new THREE.Mesh(new THREE.BufferGeometry(), original);
    body.name = 'Car_Painted_Body';
    car.add(body);
    scene.add(pavement, car);
    environment.prepareModel(scene);
    const diffuse = pavement.material as THREE.Material;
    assert.ok(diffuse instanceof THREE.MeshLambertMaterial);
    assert.equal(diffuse.map, texture);
    assert.equal(diffuse.normalMap, normalMap);
    assert.equal(diffuse.color.getHex(), original.color.getHex());
    assert.equal(pavement.receiveShadow, true);
    assert.equal(body.material, original);
    environment.update(Date.parse('2026-11-03T21:00:00+09:00'), true);
    assert.equal(diffuse.emissive.getHex(), 0);
    environment.dispose();
    diffuse.dispose();
    texture.dispose();
    normalMap.dispose();
    pavement.geometry.dispose();
    body.geometry.dispose();
});
