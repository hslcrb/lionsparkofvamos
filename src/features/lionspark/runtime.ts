import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
    canStepTo,
    EYE_HEIGHT,
    movementDelta,
    parseCollisionData,
    PLAYER_RADIUS,
    RUN_SPEED,
    WALK_SPEED,
} from './navigation';
import {
    findVehicleExit,
    movePlayer,
    simulateVehicle,
    SolidIndex,
    VEHICLE_HEIGHT,
    VEHICLE_LENGTH,
    VEHICLE_WIDTH,
    type VehicleState,
} from './physics';
import { createParkClock, createParkEnvironment, type ParkTimeMode } from './environment';
import { GroundIndex } from './ground-index';

export type { ParkTimeMode } from './environment';
export type ParkView = 'walk' | 'overview' | 'drive';

export interface ParkSnapshot {
    view: ParkView;
    timeLabel: string;
    timeMode: ParkTimeMode;
    running: boolean;
    speedKmh: number;
    notice?: string;
}

export interface ParkRuntime {
    ready: Promise<void>;
    setView: (view: ParkView) => void;
    setTimeMode: (mode: ParkTimeMode) => void;
    setRunning: (running: boolean) => void;
    setBraking: (braking: boolean) => void;
    reset: () => void;
    setTouchMovement: (forward: number, strafe: number) => void;
    focus: () => void;
    dispose: () => void;
}

const MODEL_URL = '/models/lionspark.glb';
const COLLISION_URL = '/models/lionspark-collision.json';
const CELESTIAL_SKY_URL = '/models/celestial-night.png';
const START = new THREE.Vector3(0, EYE_HEIGHT, 165);
const OVERVIEW = new THREE.Vector3(255, 240, 340);

function hasName(object: THREE.Object3D, prefix: string): boolean {
    let current: THREE.Object3D | null = object;
    while (current) {
        if (current.name.toLowerCase().startsWith(prefix.toLowerCase())) return true;
        current = current.parent;
    }
    return false;
}

function disposeModel(model: THREE.Object3D) {
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    const textures = new Set<THREE.Texture>();
    model.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) return;
        geometries.add(object.geometry);
        const meshMaterials = Array.isArray(object.material) ? object.material : [object.material];
        for (const material of meshMaterials) {
            materials.add(material);
            for (const value of Object.values(material)) {
                if (value instanceof THREE.Texture) textures.add(value);
            }
        }
    });
    for (const texture of textures) texture.dispose();
    for (const material of materials) material.dispose();
    for (const geometry of geometries) geometry.dispose();
}

async function fetchModel(signal: AbortSignal, onProgress: (value: number) => void) {
    const response = await fetch(MODEL_URL, { signal });
    if (!response.ok) throw new Error('라팍 모델을 불러오지 못했습니다.');
    const length = Number(response.headers.get('content-length'));
    if (!response.body || !Number.isFinite(length) || length <= 0) {
        return response.arrayBuffer();
    }
    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let received = 0;
    for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        received += value.byteLength;
        onProgress(Math.min(0.9, (received / length) * 0.9));
    }
    const data = new Uint8Array(received);
    let offset = 0;
    for (const chunk of chunks) {
        data.set(chunk, offset);
        offset += chunk.byteLength;
    }
    return data.buffer;
}

async function loadCelestialTexture(signal: AbortSignal): Promise<THREE.Texture> {
    const response = await fetch(CELESTIAL_SKY_URL, { signal });
    if (!response.ok) throw new Error('밤하늘을 불러오지 못했습니다.');
    const blob = await response.blob();
    signal.throwIfAborted();
    const url = URL.createObjectURL(blob);
    try {
        const texture = await new THREE.TextureLoader().loadAsync(url);
        if (signal.aborted) {
            texture.dispose();
            signal.throwIfAborted();
        }
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        texture.generateMipmaps = true;
        texture.minFilter = THREE.LinearMipmapLinearFilter;
        texture.magFilter = THREE.LinearFilter;
        return texture;
    } finally {
        URL.revokeObjectURL(url);
    }
}

export function createParkRuntime(
    host: HTMLDivElement,
    onProgress: (value: number) => void,
    onState?: (state: ParkSnapshot) => void,
): ParkRuntime {
    const renderer = new THREE.WebGLRenderer({
        antialias: true,
        powerPreference: 'high-performance',
        logarithmicDepthBuffer: true,
    });
    const coarse = window.matchMedia('(pointer: coarse)').matches;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.shadowMap.autoUpdate = false;
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(65, 1, 0.2, 2600);
    const spawn = START.clone();
    const overviewPosition = OVERVIEW.clone();
    const playerPosition = spawn.clone();
    camera.position.copy(START);
    camera.rotation.order = 'YXZ';
    const clock = createParkClock();
    const environment = createParkEnvironment(scene, renderer, coarse);
    environment.update(clock.read().epochMs, true, camera.position);

    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.target.set(0, 15, 0);
    orbit.enabled = false;
    orbit.enableDamping = true;
    orbit.minDistance = 80;
    orbit.maxDistance = 700;
    orbit.maxPolarAngle = Math.PI / 2 - 0.02;

    const keys = new Set<string>();
    const touch = { forward: 0, strafe: 0 };
    const groundMeshes: THREE.Mesh[] = [];
    const cameraMeshes: THREE.Mesh[] = [];
    let solids = new SolidIndex([]);
    let groundIndex: GroundIndex | null = null;
    const raycaster = new THREE.Raycaster();
    const cameraHits: THREE.Intersection<THREE.Object3D>[] = [];
    const chaseTarget = new THREE.Vector3();
    const chaseDesired = new THREE.Vector3();
    const chaseDirection = new THREE.Vector3();
    const chasePosition = new THREE.Vector3();
    let model: THREE.Object3D | null = null;
    let car: THREE.Object3D | null = null;
    let vehicle: VehicleState = { x: -130, z: 235, yaw: -Math.PI / 2, speed: 0 };
    let vehicleGround = 0;
    let vehicleLift = 0.1;
    let view: ParkView = 'walk';
    let running = false;
    let braking = false;
    let notice: string | undefined;
    let noticeUntil = 0;
    let lastSnapshot = '';
    let yaw = 0;
    let pitch = -0.03;
    let disposed = false;
    let frame = 0;
    let lastTime = 0;
    let lastRender = 0;
    let ready = false;
    let drag: { id: number; x: number; y: number } | null = null;
    const controller = new AbortController();
    const draco = new DRACOLoader();
    draco.setDecoderPath('/draco/');
    draco.setWorkerLimit(coarse ? 1 : 2);
    const loader = new GLTFLoader().setDRACOLoader(draco);

    function isRunning() {
        return view === 'walk' && (running || keys.has('ShiftLeft') || keys.has('ShiftRight'));
    }

    function emitState() {
        if (disposed) return;
        if (notice && Date.now() >= noticeUntil) notice = undefined;
        const time = clock.read();
        const state: ParkSnapshot = {
            view,
            timeMode: time.timeMode,
            timeLabel: time.timeLabel,
            running: isRunning(),
            speedKmh: view === 'drive' ? Math.round(Math.abs(vehicle.speed) * 3.6) : 0,
            ...(notice ? { notice } : {}),
        };
        const serialized = JSON.stringify(state);
        if (serialized !== lastSnapshot) {
            lastSnapshot = serialized;
            onState?.(state);
        }
    }

    function showNotice(message: string) {
        notice = message;
        noticeUntil = Date.now() + 4000;
        emitState();
    }

    function groundAt(x: number, z: number, eyeY: number): number | null {
        return groundIndex?.getHeight(x, z, eyeY) ?? null;
    }

    function resetWalk() {
        playerPosition.copy(spawn);
        const ground = groundAt(spawn.x, spawn.z, spawn.y);
        if (ground !== null) playerPosition.y = ground + EYE_HEIGHT;
        camera.position.copy(playerPosition);
        yaw = 0;
        pitch = -0.03;
        camera.rotation.set(pitch, yaw, 0, 'YXZ');
        clearInput();
    }

    function collidesWithParkedCar(x: number, z: number, groundY: number) {
        if (!car) return false;
        if (
            groundY + EYE_HEIGHT <= vehicleGround + 0.05 ||
            groundY + 0.05 >= vehicleGround + VEHICLE_HEIGHT
        )
            return false;
        const dx = x - vehicle.x;
        const dz = z - vehicle.z;
        const localX = dx * Math.cos(vehicle.yaw) - dz * Math.sin(vehicle.yaw);
        const localZ = dx * Math.sin(vehicle.yaw) + dz * Math.cos(vehicle.yaw);
        return (
            Math.hypot(
                Math.max(0, Math.abs(localX) - VEHICLE_WIDTH / 2),
                Math.max(0, Math.abs(localZ) - VEHICLE_LENGTH / 2),
            ) < PLAYER_RADIUS
        );
    }

    function safeExit() {
        const exit = findVehicleExit(vehicle, vehicleGround, (point) => {
            const ground = groundAt(point.x, point.z, vehicleGround + EYE_HEIGHT);
            return (
                ground !== null &&
                canStepTo(vehicleGround, ground) &&
                !solids.collidesCircle(point.x, point.z, ground)
            );
        });
        if (!exit) {
            showNotice('내릴 공간이 없습니다. 열린 곳으로 이동해 주세요.');
            return false;
        }
        const ground = groundAt(exit.x, exit.z, vehicleGround + EYE_HEIGHT);
        if (ground === null) return false;
        playerPosition.set(exit.x, ground + EYE_HEIGHT, exit.z);
        yaw = vehicle.yaw;
        pitch = -0.03;
        return true;
    }

    function enterDrive(nearbyOnly = false) {
        if (!car || !ready) {
            showNotice('차량을 아직 불러오지 못했습니다.');
            return;
        }
        if (
            nearbyOnly &&
            (Math.hypot(playerPosition.x - vehicle.x, playerPosition.z - vehicle.z) > 4.5 ||
                Math.abs(playerPosition.y - EYE_HEIGHT - vehicleGround) > 1)
        ) {
            showNotice('차량 가까이에서 E를 눌러 탑승하세요.');
            return;
        }
        if (nearbyOnly) {
            chaseDirection.set(vehicle.x, vehicleGround + 1.2, vehicle.z).sub(playerPosition);
            const distance = chaseDirection.length();
            if (distance > 0.001) {
                raycaster.set(playerPosition, chaseDirection.divideScalar(distance));
                raycaster.far = distance;
                cameraHits.length = 0;
                raycaster.intersectObjects(cameraMeshes, false, cameraHits);
                if (cameraHits[0] && cameraHits[0].distance < distance - 0.2) {
                    showNotice('차량 문을 가로막는 장애물이 있습니다.');
                    return;
                }
            }
        }
        clearInput();
        vehicle = { ...vehicle, speed: 0, steering: 0 };
        view = 'drive';
        orbit.enabled = false;
        camera.near = 0.25;
        camera.updateProjectionMatrix();
        updateChaseCamera(1, true);
        emitState();
    }

    function setView(next: ParkView) {
        if (next === 'drive') {
            if (view !== 'drive') enterDrive();
            return;
        }
        const exiting = view === 'drive';
        if (exiting && !safeExit()) return;
        clearInput();
        vehicle = { ...vehicle, speed: 0, steering: 0 };
        view = next;
        camera.near = next === 'overview' ? 2 : 0.2;
        camera.updateProjectionMatrix();
        orbit.enabled = next === 'overview';
        if (next === 'overview') {
            camera.position.copy(overviewPosition);
            orbit.target.set(0, 15, 0);
            orbit.update();
        } else if (exiting) {
            camera.position.copy(playerPosition);
            camera.rotation.set(pitch, yaw, 0, 'YXZ');
        } else resetWalk();
        emitState();
    }

    function vehicleCanOccupy(next: VehicleState) {
        const ground = groundAt(next.x, next.z, vehicleGround + EYE_HEIGHT);
        if (
            ground === null ||
            !canStepTo(vehicleGround, ground) ||
            solids.collidesVehicle(next, ground)
        )
            return false;
        const sin = Math.sin(next.yaw);
        const cos = Math.cos(next.yaw);
        for (const side of [-0.8, 0.8]) {
            for (const end of [-1.9, 1.9]) {
                const floor = groundAt(
                    next.x + side * cos + end * sin,
                    next.z - side * sin + end * cos,
                    ground + EYE_HEIGHT,
                );
                if (floor === null || Math.abs(floor - ground) > 0.6) return false;
            }
        }
        return true;
    }

    function clampChasePosition(position: THREE.Vector3) {
        chaseDirection.subVectors(position, chaseTarget);
        const distance = chaseDirection.length();
        if (distance < 0.001) return;
        raycaster.set(chaseTarget, chaseDirection.divideScalar(distance));
        raycaster.near = 0;
        raycaster.far = distance + 0.45;
        cameraHits.length = 0;
        raycaster.intersectObjects(cameraMeshes, false, cameraHits);
        const hit = cameraHits[0];
        if (hit && hit.distance < distance + 0.45) {
            position
                .copy(chaseTarget)
                .addScaledVector(chaseDirection, Math.max(0.15, hit.distance - 0.55));
        }
    }

    function updateChaseCamera(delta: number, immediate = false) {
        chaseTarget.set(vehicle.x, vehicleGround + 1.25, vehicle.z);
        chaseDesired.set(
            vehicle.x + Math.sin(vehicle.yaw) * 8,
            vehicleGround + 4.1,
            vehicle.z + Math.cos(vehicle.yaw) * 8,
        );
        clampChasePosition(chaseDesired);
        if (immediate) chasePosition.copy(chaseDesired);
        else chasePosition.lerp(chaseDesired, 1 - Math.exp(-7 * delta));
        clampChasePosition(chasePosition);
        camera.position.copy(chasePosition);
        camera.lookAt(chaseTarget);
    }

    function keyDown(event: KeyboardEvent) {
        if (
            event.target instanceof HTMLElement &&
            event.target !== host &&
            event.target.closest('button, input, select, textarea, a, [contenteditable="true"]')
        )
            return;
        if (
            ![
                'KeyW',
                'KeyA',
                'KeyS',
                'KeyD',
                'ArrowUp',
                'ArrowDown',
                'ArrowLeft',
                'ArrowRight',
                'ShiftLeft',
                'ShiftRight',
                'Space',
                'KeyE',
            ].includes(event.code)
        )
            return;
        event.preventDefault();
        if (event.code === 'KeyE') {
            if (!event.repeat) {
                if (view === 'drive') setView('walk');
                else if (view === 'walk') enterDrive(true);
            }
            return;
        }
        keys.add(event.code);
        emitState();
    }
    function keyUp(event: KeyboardEvent) {
        keys.delete(event.code);
        emitState();
    }
    function clearInput() {
        keys.clear();
        touch.forward = 0;
        touch.strafe = 0;
        running = false;
        braking = false;
        drag = null;
    }
    function pauseInput() {
        clearInput();
        vehicle = { ...vehicle, speed: 0, steering: 0 };
        emitState();
    }
    function pointerDown(event: PointerEvent) {
        if (event.pointerType === 'mouse' && event.button !== 0) return;
        host.focus({ preventScroll: true });
        if (view !== 'walk') return;
        host.setPointerCapture(event.pointerId);
        drag = { id: event.pointerId, x: event.clientX, y: event.clientY };
    }
    function pointerMove(event: PointerEvent) {
        if (!drag || drag.id !== event.pointerId || view !== 'walk') return;
        yaw -= (event.clientX - drag.x) * 0.003;
        pitch = THREE.MathUtils.clamp(pitch - (event.clientY - drag.y) * 0.0026, -1.2, 1.2);
        drag.x = event.clientX;
        drag.y = event.clientY;
        camera.rotation.set(pitch, yaw, 0, 'YXZ');
    }
    function pointerUp(event: PointerEvent) {
        if (drag?.id === event.pointerId) drag = null;
    }
    host.addEventListener('keydown', keyDown);
    window.addEventListener('keyup', keyUp);
    window.addEventListener('blur', pauseInput);
    document.addEventListener('visibilitychange', pauseInput);
    host.addEventListener('pointerdown', pointerDown);
    host.addEventListener('pointermove', pointerMove);
    host.addEventListener('pointerup', pointerUp);
    host.addEventListener('pointercancel', pointerUp);

    const resize = new ResizeObserver(() => {
        const width = Math.max(1, host.clientWidth);
        const height = Math.max(1, host.clientHeight);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
    });
    resize.observe(host);

    function render(time: number) {
        if (disposed) return;
        frame = requestAnimationFrame(render);
        if (document.hidden || !ready) {
            lastTime = time;
            return;
        }
        if (time - lastRender < 1000 / 30) return;
        lastRender = time;
        const delta = Math.min(1, Math.max(0, (time - lastTime) / 1000));
        lastTime = time;
        const parkTime = clock.read();
        environment.update(parkTime.epochMs, false, camera.position);
        if (view === 'walk' && ready) {
            const forward =
                Number(keys.has('KeyW') || keys.has('ArrowUp')) -
                Number(keys.has('KeyS') || keys.has('ArrowDown')) +
                touch.forward;
            const strafe =
                Number(keys.has('KeyD') || keys.has('ArrowRight')) -
                Number(keys.has('KeyA') || keys.has('ArrowLeft')) +
                touch.strafe;
            if (forward || strafe) {
                const speed = isRunning() ? RUN_SPEED : WALK_SPEED;
                const movement = movementDelta(forward, strafe, yaw, speed * delta);
                let nextGround = playerPosition.y - EYE_HEIGHT;
                const next = movePlayer(playerPosition, movement, (point) => {
                    const floor = groundAt(point.x, point.z, nextGround + EYE_HEIGHT);
                    if (
                        floor === null ||
                        !canStepTo(nextGround, floor) ||
                        solids.collidesCircle(point.x, point.z, floor) ||
                        collidesWithParkedCar(point.x, point.z, floor)
                    )
                        return false;
                    nextGround = floor;
                    return true;
                });
                playerPosition.set(next.x, nextGround + EYE_HEIGHT, next.z);
                camera.position.copy(playerPosition);
            }
        } else if (view === 'drive' && car) {
            const throttle =
                Number(keys.has('KeyW') || keys.has('ArrowUp')) -
                Number(keys.has('KeyS') || keys.has('ArrowDown')) +
                touch.forward;
            const steer =
                Number(keys.has('KeyA') || keys.has('ArrowLeft')) -
                Number(keys.has('KeyD') || keys.has('ArrowRight')) -
                touch.strafe;
            vehicle = simulateVehicle(
                vehicle,
                { throttle, steer, brake: braking || keys.has('Space') },
                delta,
                vehicleCanOccupy,
            );
            const ground = groundAt(vehicle.x, vehicle.z, vehicleGround + EYE_HEIGHT);
            if (ground !== null) vehicleGround = ground;
            car.position.set(vehicle.x, vehicleGround + vehicleLift, vehicle.z);
            car.rotation.set(0, vehicle.yaw, 0);
            car.updateMatrixWorld(true);
            updateChaseCamera(delta);
        } else if (view === 'overview') orbit.update();
        environment.animate(parkTime.epochMs, camera);
        emitState();
        renderer.render(scene, camera);
    }
    frame = requestAnimationFrame(render);

    const loading = (async () => {
        const [buffer, collisionResponse] = await Promise.all([
            fetchModel(controller.signal, onProgress),
            fetch(COLLISION_URL, { signal: controller.signal }),
            loadCelestialTexture(controller.signal).then((texture) => {
                environment.setSkyTexture(texture);
            }),
        ]);
        if (!collisionResponse.ok) throw new Error('보행 경로를 불러오지 못했습니다.');
        const collisions = parseCollisionData(await collisionResponse.json());
        if (!collisions) throw new Error('보행 경로를 불러오지 못했습니다.');
        solids = new SolidIndex(collisions);
        spawn.fromArray(collisions.spawn);
        overviewPosition.fromArray(collisions.overview);
        const gltf = await loader.parseAsync(buffer, '/models/');
        if (disposed) {
            disposeModel(gltf.scene);
            return;
        }
        model = gltf.scene;
        model.updateMatrixWorld(true);
        model.traverse((object) => {
            if (!car && /^Driveable_Car(?:[._]\d+)?$/i.test(object.name)) car = object;
        });
        model.traverse((object) => {
            if (!(object instanceof THREE.Mesh)) return;
            const sky = hasName(object, 'SkyDome');
            object.castShadow = !sky && !hasName(object, 'Driveable_Car');
            object.receiveShadow = !sky;
            if (sky) {
                object.frustumCulled = false;
                const materials = Array.isArray(object.material)
                    ? object.material
                    : [object.material];
                for (const material of materials) material.fog = false;
            }
            if (hasName(object, 'WalkSurface')) groundMeshes.push(object);
            if (!sky && !hasName(object, 'Driveable_Car')) cameraMeshes.push(object);
        });
        if (!groundMeshes.length) throw new Error('보행 경로를 불러오지 못했습니다.');
        groundIndex = new GroundIndex(groundMeshes);
        scene.add(model);
        environment.prepareModel(model, collisions.nightLights);
        if (car) {
            const loadedCar = car as THREE.Object3D;
            scene.attach(loadedCar);
            const start = collisions.vehicleSpawn ?? [-130, 0.1, 235, -Math.PI / 2];
            vehicle = { x: start[0], z: start[2], yaw: start[3], speed: 0, steering: 0 };
            vehicleGround = groundAt(start[0], start[2], start[1] + EYE_HEIGHT) ?? 0;
            vehicleLift = start[1] - vehicleGround;
            loadedCar.position.set(start[0], start[1], start[2]);
            loadedCar.rotation.set(0, start[3], 0);
            loadedCar.updateMatrixWorld(true);
        }
        environment.update(clock.read().epochMs, true, camera.position);
        environment.animate(clock.read().epochMs, camera);
        await renderer.compileAsync(scene, camera);
        if (disposed) return;
        renderer.shadowMap.needsUpdate = true;
        ready = true;
        resetWalk();
        onProgress(1);
        emitState();
    })().catch((error: unknown) => {
        controller.abort();
        throw error;
    });

    return {
        ready: loading,
        setView,
        setTimeMode: (mode) => {
            clock.setMode(mode);
            environment.update(clock.read().epochMs, true, camera.position);
            emitState();
        },
        setRunning: (value) => {
            running = value;
            emitState();
        },
        setBraking: (value) => {
            braking = value;
        },
        reset: () => {
            clearInput();
            vehicle = { ...vehicle, speed: 0, steering: 0 };
            view = 'walk';
            orbit.enabled = false;
            camera.near = 0.2;
            camera.updateProjectionMatrix();
            resetWalk();
            emitState();
        },
        setTouchMovement: (forward, strafe) => {
            touch.forward = THREE.MathUtils.clamp(forward, -1, 1);
            touch.strafe = THREE.MathUtils.clamp(strafe, -1, 1);
        },
        focus: () => host.focus({ preventScroll: true }),
        dispose: () => {
            disposed = true;
            controller.abort();
            cancelAnimationFrame(frame);
            resize.disconnect();
            orbit.dispose();
            draco.dispose();
            host.removeEventListener('keydown', keyDown);
            window.removeEventListener('keyup', keyUp);
            window.removeEventListener('blur', pauseInput);
            document.removeEventListener('visibilitychange', pauseInput);
            host.removeEventListener('pointerdown', pointerDown);
            host.removeEventListener('pointermove', pointerMove);
            host.removeEventListener('pointerup', pointerUp);
            host.removeEventListener('pointercancel', pointerUp);
            disposeModel(scene);
            environment.dispose();
            renderer.dispose();
            renderer.domElement.remove();
        },
    };
}
