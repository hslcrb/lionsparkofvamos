'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

interface Props {
    moving: boolean;
}

export default function GlassEmblem({ moving }: Props) {
    const host = useRef<HTMLSpanElement>(null);
    const movingRef = useRef(moving);
    useEffect(() => {
        movingRef.current = moving;
    }, [moving]);

    useEffect(() => {
        const element = host.current;
        if (!element) return;
        let renderer: THREE.WebGLRenderer;
        try {
            renderer = new THREE.WebGLRenderer({
                alpha: true,
                antialias: true,
                powerPreference: 'low-power',
            });
        } catch {
            return;
        }
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
        renderer.setClearColor(0x000000, 0);
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.35;
        element.appendChild(renderer.domElement);

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 40);
        camera.position.set(0, 0.15, 6.5);
        camera.lookAt(0, 0, 0);
        const pmrem = new THREE.PMREMGenerator(renderer);
        const studio = new RoomEnvironment();
        const environment = pmrem.fromScene(studio, 0.025);
        scene.environment = environment.texture;
        studio.dispose();
        pmrem.dispose();

        const group = new THREE.Group();
        scene.add(group);
        const glassGeometry = new RoundedBoxGeometry(2.75, 2.75, 0.52, 8, 0.21);
        const glassMaterial = new THREE.MeshPhysicalMaterial({
            color: 0xffffff,
            metalness: 0,
            roughness: 0.025,
            transmission: 0.98,
            thickness: 0.7,
            ior: 1.49,
            clearcoat: 1,
            clearcoatRoughness: 0.03,
            attenuationColor: new THREE.Color(0x98d8ff),
            attenuationDistance: 3.5,
            envMapIntensity: 1.5,
        });
        const glass = new THREE.Mesh(glassGeometry, glassMaterial);
        group.add(glass);

        let disposed = false;

        const backdropGeometry = new THREE.PlaneGeometry(14, 14);
        const backdropMaterial = new THREE.ShaderMaterial({
            uniforms: { time: { value: 0 } },
            vertexShader: `varying vec2 vUv; void main() { vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
            fragmentShader: `
                varying vec2 vUv; uniform float time;
                void main() {
                    float light = sin(vUv.x*22.+sin(vUv.y*6.+time*.16)*.7)*.5+.5;
                    vec3 color = mix(vec3(.70,.87,.97),vec3(.92,.98,1.),vUv.y);
                    color += pow(light,14.)*.055;
                    gl_FragColor=vec4(color,1.);
                }`,
        });
        const backdrop = new THREE.Mesh(backdropGeometry, backdropMaterial);
        backdrop.position.z = -2;
        scene.add(backdrop);
        scene.add(new THREE.HemisphereLight(0xeafaff, 0x0b5099, 2.0));
        const key = new THREE.DirectionalLight(0xffffff, 3.2);
        key.position.set(-3, 5, 6);
        scene.add(key);
        const rim = new THREE.DirectionalLight(0x82c9ff, 2);
        rim.position.set(4, 0, 4);
        scene.add(rim);

        const pointer = { x: 0, y: 0 };
        const button = element.closest('button');
        function onPointer(event: PointerEvent) {
            if (!button || event.pointerType === 'touch') return;
            const bounds = button.getBoundingClientRect();
            pointer.x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 0.25;
            pointer.y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 0.18;
        }
        function resetPointer() {
            pointer.x = 0;
            pointer.y = 0;
        }
        button?.addEventListener('pointermove', onPointer);
        button?.addEventListener('pointerleave', resetPointer);

        const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
        let visible = true;
        let frame = 0;
        let lastRender = 0;
        let renderedStatic = false;
        const started = performance.now();
        function render(now: number) {
            if (disposed) return;
            frame = requestAnimationFrame(render);
            if (!visible || document.hidden || now - lastRender < 1000 / 30) return;
            lastRender = now;
            const animate = movingRef.current && !reduced.matches;
            if (!animate && renderedStatic) return;
            renderedStatic = !animate;
            const time = (now - started) / 1000;
            const rotationX = -0.12 + (animate ? Math.sin(time * 0.48) * 0.055 + pointer.y : 0);
            const rotationY = -0.16 + (animate ? Math.sin(time * 0.38) * 0.13 + pointer.x : 0);
            group.rotation.x = animate
                ? group.rotation.x + (rotationX - group.rotation.x) * 0.09
                : rotationX;
            group.rotation.y = animate
                ? group.rotation.y + (rotationY - group.rotation.y) * 0.09
                : rotationY;
            group.rotation.z = -0.055;
            group.position.y = animate ? Math.sin(time * 0.64) * 0.065 : 0;
            if (animate) backdropMaterial.uniforms.time!.value = time;
            renderer.render(scene, camera);
        }
        const resize = new ResizeObserver(() => {
            renderedStatic = false;
            const width = Math.max(1, element.clientWidth);
            const height = Math.max(1, element.clientHeight);
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
            renderer.setSize(width, height, false);
        });
        resize.observe(element);
        const observer = new IntersectionObserver(([entry]) => {
            visible = entry?.isIntersecting ?? false;
        });
        observer.observe(element);
        frame = requestAnimationFrame(render);
        element.dataset.ready = 'true';

        return () => {
            disposed = true;
            cancelAnimationFrame(frame);
            resize.disconnect();
            observer.disconnect();
            button?.removeEventListener('pointermove', onPointer);
            button?.removeEventListener('pointerleave', resetPointer);
            glassMaterial.dispose();
            glassGeometry.dispose();
            backdropMaterial.dispose();
            backdropGeometry.dispose();
            environment.dispose();
            renderer.dispose();
            renderer.domElement.remove();
            delete element.dataset.ready;
        };
    }, []);

    return <span ref={host} className="glass-emblem" aria-hidden="true" />;
}
