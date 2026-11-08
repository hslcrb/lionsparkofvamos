import * as THREE from 'three';
import { Sky } from 'three/examples/jsm/objects/Sky.js';
import { sampleCelestial } from './astronomy';

// Reuse Three's wavelength dependent Rayleigh / Mie atmosphere on the Blender dome.
// The photographic cloud layer replaces the default procedural cloud noise passes.
const skyShader = Sky.SkyShader as {
    uniforms: Record<string, THREE.IUniform>;
    vertexShader: string;
    fragmentShader: string;
};

const celestialDeclarations = /* glsl */ `
    varying vec2 vSkyUv;
    uniform sampler2D uNightMap;
    uniform sampler2D uCloudMap;
    uniform float uHasNightMap;
    uniform float uHasCloudMap;
    uniform float uNightVisibility;
    uniform float uAtmosphereVisibility;
    uniform float uSunAltitude;
    uniform float uAnimationTime;
    uniform float uCloudPhase;
    uniform vec3 uRa0;
    uniform vec3 uRa90;
    uniform vec3 uNorthPole;
    uniform vec3 uMoonDirection;
    uniform float uMoonIllumination;

    float skyHash(float value) {
        return fract(sin(value * 12.9898 + 78.233) * 43758.5453);
    }

    vec3 meteorRadiance(vec3 direction) {
        vec2 angular = vec2(atan(direction.z, direction.x), asin(clamp(direction.y, -1.0, 1.0)));
        float light = 0.0;
        // Two brief, separated events per thirty seconds; no geometry or particle system.
        for (int lane = 0; lane < 2; lane++) {
            float clock = uAnimationTime + float(lane) * 14.0;
            float age = mod(clock, 30.0);
            if (age < 0.95) {
                float seed = floor(clock / 30.0) + float(lane) * 47.0;
                vec2 start = vec2(skyHash(seed) * 5.5 - 2.75, 0.5 + skyHash(seed + 9.0) * 0.65);
                vec2 velocity = vec2(0.40 + skyHash(seed + 3.0) * 0.25, -0.29);
                vec2 head = start + velocity * age;
                vec2 tail = head - velocity * 0.22;
                vec2 delta = angular - tail;
                delta.x = atan(sin(delta.x), cos(delta.x));
                vec2 segment = head - tail;
                float along = clamp(dot(delta, segment) / dot(segment, segment), 0.0, 1.0);
                float distanceToTrail = length(delta - segment * along);
                float envelope = smoothstep(0.0, 0.12, age) * (1.0 - smoothstep(0.55, 0.95, age));
                light += exp(-pow(distanceToTrail / 0.0010, 2.0)) * pow(along, 2.5) * envelope * 1.8;
            }
        }
        return vec3(0.83, 0.88, 1.0) * light;
    }
`;

const celestialComposite = /* glsl */ `
    float aboveHorizon = smoothstep(-0.012, 0.11, direction.y);
    float horizonHaze = exp(-max(direction.y, 0.0) * 8.5);
    float sunFacing = pow(max(0.0, dot(normalize(vec3(direction.x, 0.04, direction.z)),
        normalize(vec3(vSunDirection.x, 0.04, vSunDirection.z)))), 5.0);
    float golden = exp(-pow((uSunAltitude + 0.025) / 0.115, 2.0));
    vec3 afterglow = vec3(0.30, 0.059, 0.012) * golden * sunFacing * horizonHaze;
    texColor = texColor * uAtmosphereVisibility + afterglow;

    if (uHasCloudMap > 0.5 && uAtmosphereVisibility > 0.01) {
        vec2 cloudUv = vec2(fract(vSkyUv.x + uCloudPhase), vSkyUv.y);
        vec3 photograph = texture2D(uCloudMap, cloudUv).rgb;
        float cloudLuma = dot(photograph, vec3(0.2126, 0.7152, 0.0722));
        // Bright, nearly neutral parts of the original sky image supply soft cloud detail.
        float cloudMask = smoothstep(0.17, 0.65, cloudLuma) *
            (1.0 - smoothstep(0.03, 0.30, photograph.b - photograph.r));
        vec3 cloudLight = mix(vec3(0.43, 0.46, 0.52), vec3(0.95, 0.76, 0.57), golden * sunFacing);
        float dayCloud = smoothstep(-0.10, 0.12, uSunAltitude);
        texColor = mix(texColor, cloudLight * (0.38 + cloudLuma * 0.48),
            cloudMask * 0.52 * dayCloud * aboveHorizon);
    }

    if (uNightVisibility > 0.001) {
        vec3 equatorial = normalize(vec3(dot(direction, uRa0), dot(direction, uRa90), dot(direction, uNorthPole)));
        vec2 starUv = vec2(atan(equatorial.y, equatorial.x) / (2.0 * pi) + 0.5,
            asin(clamp(equatorial.z, -1.0, 1.0)) / pi + 0.5);
        vec3 stars = texture2D(uNightMap, starUv).rgb * uHasNightMap;
        float starLuma = dot(stars, vec3(0.2126, 0.7152, 0.0722));
        vec2 cell = floor(starUv * vec2(4096.0, 2048.0));
        float starSeed = skyHash(dot(cell, vec2(1.0, 131.0)));
        float twinkle = sin(uAnimationTime * (1.7 + starSeed * 4.0) + starSeed * 6.283185);
        stars *= 1.0 + twinkle * 0.14 * smoothstep(0.04, 0.45, starLuma);

        float moonAboveHorizon = smoothstep(-0.03, 0.12, uMoonDirection.y);
        float moonlight = uMoonIllumination * moonAboveHorizon;
        float moonCos = dot(direction, uMoonDirection);
        float moonHalo = exp(-max(0.0, 1.0 - moonCos) * 220.0) * moonlight;
        vec3 nightAir = vec3(0.0010, 0.0018, 0.0034) +
            vec3(0.012, 0.010, 0.008) * horizonHaze + vec3(0.006, 0.008, 0.013) * moonHalo;
        vec3 nightRadiance = nightAir + stars * 1.65 * aboveHorizon *
            (1.0 - horizonHaze * 0.85) * (1.0 - moonlight * 0.28) * (1.0 - moonHalo * 0.65);

        const float moonRadius = 0.0052;
        if (moonCos > cos(moonRadius * 1.1)) {
            vec3 moonRight = normalize(cross(uMoonDirection, vec3(0.0001, 1.0, 0.0)));
            vec3 moonUp = cross(moonRight, uMoonDirection);
            vec2 lunar = vec2(dot(direction, moonRight), dot(direction, moonUp)) / moonRadius;
            float radiusSquared = dot(lunar, lunar);
            float disc = 1.0 - smoothstep(0.90, 1.0, radiusSquared);
            vec3 normal = moonRight * lunar.x + moonUp * lunar.y -
                uMoonDirection * sqrt(max(0.0, 1.0 - radiusSquared));
            float lit = max(0.0, dot(normal, vSunDirection));
            float maria = 0.86 + 0.07 * sin(lunar.x * 18.0 + sin(lunar.y * 11.0)) * cos(lunar.y * 14.0);
            vec3 lunarLight = vec3(0.82, 0.85, 0.89) * (lit * 1.45 + 0.012) * maria;
            nightRadiance = mix(nightRadiance, lunarLight, disc * aboveHorizon);
        }
        nightRadiance += meteorRadiance(direction) * aboveHorizon;
        texColor += nightRadiance * uNightVisibility;
    }
`;

export function createCelestialSky(
    mesh: THREE.Mesh,
    cloudMap: THREE.Texture | null,
    nightMap: THREE.Texture | null,
) {
    const uniforms = THREE.UniformsUtils.clone(skyShader.uniforms);
    Object.assign(uniforms, {
        uNightMap: { value: nightMap },
        uCloudMap: { value: cloudMap },
        uHasNightMap: { value: nightMap ? 1 : 0 },
        uHasCloudMap: { value: cloudMap ? 1 : 0 },
        uNightVisibility: { value: 0 },
        uAtmosphereVisibility: { value: 1 },
        uSunAltitude: { value: 0 },
        uAnimationTime: { value: 0 },
        uCloudPhase: { value: 0 },
        uRa0: { value: new THREE.Vector3() },
        uRa90: { value: new THREE.Vector3() },
        uNorthPole: { value: new THREE.Vector3() },
        uMoonDirection: { value: new THREE.Vector3() },
        uMoonIllumination: { value: 0 },
        uSkyCenter: { value: new THREE.Vector3() },
    });
    if (mesh.geometry.getAttribute('position')) {
        mesh.geometry.computeBoundingSphere();
        uniforms.uSkyCenter!.value.copy(
            mesh.geometry.boundingSphere?.center ?? new THREE.Vector3(),
        );
    }
    uniforms.turbidity!.value = 2.7;
    uniforms.rayleigh!.value = 2.1;
    uniforms.mieCoefficient!.value = 0.004;
    uniforms.mieDirectionalG!.value = 0.82;
    uniforms.cloudCoverage!.value = 0;
    const vertexShader = skyShader.vertexShader
        .replace(
            'void main() {',
            'varying vec2 vSkyUv;\nuniform vec3 uSkyCenter;\nvoid main() {\nvSkyUv = uv;',
        )
        .replace(
            'vWorldPosition = worldPosition.xyz;',
            'vWorldPosition = mat3(modelMatrix) * (position - uSkyCenter);',
        )
        .replace(
            'gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );',
            'gl_Position = projectionMatrix * vec4(mat3(viewMatrix) * vWorldPosition, 1.0);',
        );
    const fragmentShader = skyShader.fragmentShader
        .replace('void main() {', `${celestialDeclarations}\nvoid main() {`)
        .replace('normalize( vWorldPosition - cameraPosition )', 'normalize( vWorldPosition )')
        .replace(/\/\/ Clouds[\s\S]*?(?=gl_FragColor =)/, celestialComposite);
    const material = new THREE.ShaderMaterial({
        name: 'Blender_Dome_Celestial_Atmosphere',
        uniforms,
        vertexShader,
        fragmentShader,
        side: THREE.DoubleSide,
        depthTest: false,
        depthWrite: false,
        fog: false,
    });
    mesh.frustumCulled = false;
    mesh.renderOrder = -1000;
    mesh.castShadow = false;
    mesh.receiveShadow = false;

    return {
        material,
        setNightMap(texture: THREE.Texture) {
            uniforms.uNightMap!.value = texture;
            uniforms.uHasNightMap!.value = 1;
        },
        update(epochMs: number) {
            const celestial = sampleCelestial(epochMs);
            const altitude = celestial.sunAltitudeRadians;
            uniforms.sunPosition!.value.copy(celestial.sunDirection).multiplyScalar(450_000);
            uniforms.uSunAltitude!.value = altitude;
            uniforms.uNightVisibility!.value =
                1 - THREE.MathUtils.smoothstep(altitude, -0.24, -0.075);
            uniforms.uAtmosphereVisibility!.value = THREE.MathUtils.smoothstep(
                altitude,
                -0.23,
                0.012,
            );
            uniforms.uAnimationTime!.value = (((epochMs / 1000) % 86_400) + 86_400) % 86_400;
            uniforms.uCloudPhase!.value = ((((epochMs / 1000) * 0.000003) % 1) + 1) % 1;
            uniforms.uRa0!.value.copy(celestial.equatorialBasis.ra0);
            uniforms.uRa90!.value.copy(celestial.equatorialBasis.ra90);
            uniforms.uNorthPole!.value.copy(celestial.equatorialBasis.northPole);
            uniforms.uMoonDirection!.value.copy(celestial.moonDirection);
            uniforms.uMoonIllumination!.value = celestial.moonIllumination;
        },
    };
}
