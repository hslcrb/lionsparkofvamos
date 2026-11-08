import * as THREE from 'three';
import type { Dance } from '../room';
type Vector3 = [number, number, number];
type Ref<T> = { current: T };
export interface CinemaView {
    entered: boolean;
    pan: number;
}

const palette = {
    navy: 0x102d78,
    blue: 0x2459c4,
    paleBlue: 0x9fc7ff,
    cream: 0xfff0d2,
    orange: 0xffbd6d,
    dark: 0x142553,
    pink: 0xffa9ad,
};

function material(
    color: THREE.ColorRepresentation,
    extra: THREE.MeshStandardMaterialParameters = {},
) {
    return new THREE.MeshStandardMaterial({ color, roughness: 0.8, ...extra });
}

function ellipsoid(
    parent: THREE.Object3D,
    color: THREE.ColorRepresentation,
    position: Vector3,
    scale: Vector3,
    extra: THREE.MeshStandardMaterialParameters = {},
) {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), material(color, extra));
    mesh.position.set(...position);
    mesh.scale.set(...scale);
    parent.add(mesh);
    return mesh;
}

function box(
    parent: THREE.Object3D,
    color: THREE.ColorRepresentation,
    position: Vector3,
    scale: Vector3,
    extra: THREE.MeshStandardMaterialParameters = {},
) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), material(color, extra));
    mesh.position.set(...position);
    mesh.scale.set(...scale);
    parent.add(mesh);
    return mesh;
}

function makeLion(x: number, outfit: THREE.ColorRepresentation, size = 1) {
    const lion = new THREE.Group();
    lion.position.set(x, -1.2, 0.8);
    lion.scale.setScalar(size);

    // Mane and face are layered like soft, rounded clay pieces.
    ellipsoid(lion, 0xdd8c3c, [0, 1.18, 0], [0.83, 0.86, 0.34]);
    ellipsoid(lion, 0xf5b65e, [-0.57, 1.75, 0.07], [0.22, 0.23, 0.15]);
    ellipsoid(lion, 0xf5b65e, [0.57, 1.75, 0.07], [0.22, 0.23, 0.15]);
    ellipsoid(lion, 0xffd790, [0, 1.21, 0.28], [0.65, 0.63, 0.3]);
    ellipsoid(lion, 0xffe4af, [0, 0.98, 0.52], [0.32, 0.22, 0.12]);
    ellipsoid(lion, palette.dark, [-0.24, 1.27, 0.55], [0.045, 0.065, 0.035]);
    ellipsoid(lion, palette.dark, [0.24, 1.27, 0.55], [0.045, 0.065, 0.035]);
    ellipsoid(lion, 0x714a32, [0, 1.08, 0.64], [0.09, 0.06, 0.04]);
    ellipsoid(lion, palette.pink, [-0.39, 1.04, 0.52], [0.09, 0.04, 0.02]);
    ellipsoid(lion, palette.pink, [0.39, 1.04, 0.52], [0.09, 0.04, 0.02]);

    ellipsoid(lion, outfit, [0, 0.05, 0], [0.7, 0.67, 0.42]);
    ellipsoid(lion, 0xffd790, [-0.35, -0.43, 0.37], [0.24, 0.18, 0.21]);
    ellipsoid(lion, 0xffd790, [0.35, -0.43, 0.37], [0.24, 0.18, 0.21]);

    const leftArm = new THREE.Group();
    leftArm.position.set(-0.57, 0.32, 0.15);
    ellipsoid(leftArm, 0xffd790, [-0.18, -0.17, 0], [0.18, 0.33, 0.18]);
    lion.add(leftArm);
    const rightArm = new THREE.Group();
    rightArm.position.set(0.57, 0.32, 0.15);
    ellipsoid(rightArm, 0xffd790, [0.18, -0.17, 0], [0.18, 0.33, 0.18]);
    lion.add(rightArm);

    // A little ball cap makes each character feel like a supporter.
    ellipsoid(lion, palette.blue, [0, 1.71, 0.29], [0.55, 0.18, 0.29]);
    ellipsoid(lion, 0x183f9a, [0, 1.62, 0.57], [0.42, 0.055, 0.21]);
    return { group: lion, leftArm, rightArm, baseY: lion.position.y };
}

function screenTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 512;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Canvas 2D is unavailable');
    const gradient = context.createLinearGradient(0, 0, 1024, 512);
    gradient.addColorStop(0, '#1b48b2');
    gradient.addColorStop(1, '#568bed');
    context.fillStyle = gradient;
    context.fillRect(0, 0, 1024, 512);
    context.textAlign = 'center';
    context.fillStyle = '#c3dcff';
    context.font = '700 35px sans-serif';
    context.fillText('THE LIONS CINEMA', 512, 105);
    context.fillStyle = '#fff7df';
    context.font = '900 170px sans-serif';
    context.fillText('VAMOS!', 512, 290);
    context.font = '700 34px sans-serif';
    context.fillStyle = '#e4edff';
    context.fillText('OUR BLUE, OUR CHEER', 512, 370);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
}

export function makeScene(
    host: HTMLDivElement,
    danceRef: Ref<Dance>,
    viewRef: Ref<CinemaView>,
    setUnavailable: (value: boolean) => void,
) {
    let renderer;
    try {
        renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: 'low-power',
        });
    } catch {
        setUnavailable(true);
        return () => {};
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setClearColor(0x162b69, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-4, 4, 3.7, -3.7, 0.1, 100);
    camera.position.set(0, 0.3, 15);
    camera.lookAt(0, 0, 0);
    scene.add(new THREE.HemisphereLight(0xe0edff, 0x8a5c51, 2.5));
    const warm = new THREE.DirectionalLight(0xffe2bd, 2.1);
    warm.position.set(-4, 6, 8);
    scene.add(warm);

    // Theater frame, screen, and a line of warm festoon lights.
    box(scene, 0x183679, [0, 0, -2.5], [9.8, 7.6, 0.1]);
    box(scene, 0x3153a2, [0, -2.9, -1.8], [9.8, 1.8, 0.2]);
    box(scene, 0xffd999, [0, 1.42, -1.8], [5.1, 2.7, 0.2]);
    const screen = new THREE.Mesh(
        new THREE.PlaneGeometry(4.78, 2.38),
        new THREE.MeshBasicMaterial({ map: screenTexture() }),
    );
    screen.position.set(0, 1.42, -1.67);
    scene.add(screen);
    for (let i = 0; i < 11; i += 1) {
        const x = -3.6 + i * 0.72;
        const y = 3.12 - 0.18 * Math.cos(((i - 5) * Math.PI) / 10);
        ellipsoid(scene, 0xffdb91, [x, y, -1.2], [0.055, 0.055, 0.055], {
            emissive: 0xffb54a,
            emissiveIntensity: 0.7,
        });
    }
    // Curtain rolls frame the room without hiding the characters.
    for (const side of [-1, 1]) {
        for (let i = 0; i < 3; i += 1) {
            ellipsoid(
                scene,
                i % 2 ? 0x709ff0 : 0x5888e0,
                [side * (3.5 + i * 0.23), 0.4, -1],
                [0.28, 3.0, 0.22],
            );
        }
        ellipsoid(scene, 0xffdba5, [side * 3.58, -0.2, -0.65], [0.42, 0.15, 0.15]);
    }

    // A shared sofa and a patchwork blanket keep the scene cozy.
    ellipsoid(scene, 0x709eec, [0, -1.65, -0.1], [3.45, 0.9, 0.45]);
    ellipsoid(scene, 0x95bcfa, [0, -2.48, 0.5], [3.55, 0.65, 0.56]);
    ellipsoid(scene, 0xd0e2ff, [0, -2.59, 1.22], [2.45, 0.49, 0.22]);
    for (let i = -2; i <= 2; i += 1) {
        ellipsoid(scene, 0xf7f4e8, [i * 0.8, -2.48, 1.43], [0.07, 0.07, 0.035]);
    }
    ellipsoid(scene, 0xffe6b4, [-3.05, -2.12, 0.8], [0.6, 0.48, 0.32]);
    ellipsoid(scene, 0xffe6b4, [3.05, -2.12, 0.8], [0.6, 0.48, 0.32]);

    const lions = [
        makeLion(-1.95, 0xe5f0ff, 0.84),
        makeLion(0, 0x4181e6, 1),
        makeLion(1.95, 0xf6f2df, 0.84),
    ];
    lions.forEach(({ group }) => scene.add(group));

    const sparkleGeometry = new THREE.SphereGeometry(0.065, 10, 8);
    const sparkleMaterial = new THREE.MeshBasicMaterial({ color: 0xffe5a8 });
    const sparkles: THREE.Mesh[] = [];
    for (let i = 0; i < 12; i += 1) {
        const sparkle = new THREE.Mesh(sparkleGeometry, sparkleMaterial);
        sparkle.position.set(-3.3 + (i % 6) * 1.32, -0.1 + Math.floor(i / 6) * 1.25, 2);
        sparkle.scale.setScalar(i % 3 === 0 ? 1 : 0.55);
        scene.add(sparkle);
        sparkles.push(sparkle);
    }

    const resize = () => {
        const width = Math.max(host.clientWidth, 1);
        const height = Math.max(host.clientHeight, 1);
        const aspect = width / height;
        const halfHeight = Math.max(3.7, 4.15 / aspect);
        camera.left = -halfHeight * aspect;
        camera.right = halfHeight * aspect;
        camera.top = halfHeight;
        camera.bottom = -halfHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const startedAt = performance.now();
    let frame = 0;
    const animate = () => {
        const time = (performance.now() - startedAt) / 1000;
        const dance = danceRef.current;
        const view = viewRef.current;
        const targetZoom = view.entered ? 1.22 : 1;
        const targetX = view.entered ? view.pan * 2 : 0;
        const easing = reducedMotion.matches ? 1 : 0.08;
        camera.zoom += (targetZoom - camera.zoom) * easing;
        camera.position.x += (targetX - camera.position.x) * easing;
        camera.lookAt(0, 0, 0);
        camera.updateProjectionMatrix();
        lions.forEach((lion, index) => {
            const offset = index * 0.55;
            const moving = !reducedMotion.matches && dance !== 'idle';
            const beat = time * (dance === 'jump' ? 7 : 5) + offset;
            lion.group.position.y =
                lion.baseY + (moving && dance === 'jump' ? Math.abs(Math.sin(beat)) * 0.34 : 0);
            lion.group.rotation.z = moving ? Math.sin(beat) * (dance === 'wave' ? 0.13 : 0.2) : 0;
            lion.leftArm.rotation.z = moving ? -1.2 - Math.sin(beat) * 0.35 : 0.3;
            lion.rightArm.rotation.z = moving
                ? 1.2 + Math.sin(beat + (dance === 'wave' ? 1.6 : 0)) * 0.35
                : -0.3;
        });
        sparkles.forEach((sparkle, index) => {
            sparkle.visible = dance !== 'idle' && (!reducedMotion.matches || index % 2 === 0);
        });
        renderer.render(scene, camera);
        frame = requestAnimationFrame(animate);
    };
    animate();

    return () => {
        cancelAnimationFrame(frame);
        observer.disconnect();
        scene.traverse((object) => {
            if (!(object instanceof THREE.Mesh)) return;
            object.geometry.dispose();
            if (object.material) {
                const materials = Array.isArray(object.material)
                    ? object.material
                    : [object.material];
                materials.forEach((item: THREE.Material) => {
                    if ('map' in item && item.map instanceof THREE.Texture) item.map.dispose();
                    item.dispose();
                });
            }
        });
        renderer.dispose();
        renderer.domElement.remove();
    };
}
