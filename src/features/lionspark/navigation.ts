export interface HorizontalPoint {
    x: number;
    z: number;
}

export interface CollisionBox {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
    minZ: number;
    maxZ: number;
}

// 개별 물체와 야간 조명 자료 / Individual solids and night light metadata
export interface CollisionSolid {
    cx: number;
    cz: number;
    hx: number;
    hz: number;
    yaw: number;
    minY: number;
    maxY: number;
}

export interface NightLightAnchor {
    position: [number, number, number];
    target: [number, number, number];
    kind: 'flood' | 'facade' | 'road';
}

export interface ParkCollisionData {
    boxes: CollisionBox[];
    solids?: CollisionSolid[];
    spawn: [number, number, number];
    overview: [number, number, number];
    vehicleSpawn?: [number, number, number, number];
    nightLights?: NightLightAnchor[];
}

function isPoint(value: unknown): value is [number, number, number] {
    return Array.isArray(value) && value.length === 3 && value.every(Number.isFinite);
}

function isCollisionBox(value: unknown): value is CollisionBox {
    if (typeof value !== 'object' || value === null) return false;
    const box = value as Record<string, unknown>;
    const keys = ['minX', 'maxX', 'minY', 'maxY', 'minZ', 'maxZ'] as const;
    if (!keys.every((key) => typeof box[key] === 'number' && Number.isFinite(box[key])))
        return false;
    return (
        (box.minX as number) <= (box.maxX as number) &&
        (box.minY as number) <= (box.maxY as number) &&
        (box.minZ as number) <= (box.maxZ as number)
    );
}

function isCollisionSolid(value: unknown): value is CollisionSolid {
    if (typeof value !== 'object' || value === null) return false;
    const solid = value as Record<string, unknown>;
    const keys = ['cx', 'cz', 'hx', 'hz', 'yaw', 'minY', 'maxY'] as const;
    return (
        keys.every((key) => typeof solid[key] === 'number' && Number.isFinite(solid[key])) &&
        (solid.hx as number) >= 0 &&
        (solid.hz as number) >= 0 &&
        (solid.minY as number) <= (solid.maxY as number)
    );
}

function isNightLight(value: unknown): value is NightLightAnchor {
    if (typeof value !== 'object' || value === null) return false;
    const light = value as Record<string, unknown>;
    return (
        isPoint(light.position) &&
        isPoint(light.target) &&
        ['flood', 'facade', 'road'].includes(light.kind as string)
    );
}

export function parseCollisionData(value: unknown): ParkCollisionData | null {
    if (typeof value !== 'object' || value === null) return null;
    const data = value as Record<string, unknown>;
    if (
        !Array.isArray(data.boxes) ||
        !data.boxes.every(isCollisionBox) ||
        !isPoint(data.spawn) ||
        !isPoint(data.overview) ||
        (data.solids !== undefined &&
            (!Array.isArray(data.solids) || !data.solids.every(isCollisionSolid))) ||
        (data.vehicleSpawn !== undefined &&
            (!Array.isArray(data.vehicleSpawn) ||
                data.vehicleSpawn.length !== 4 ||
                !data.vehicleSpawn.every(Number.isFinite))) ||
        (data.nightLights !== undefined &&
            (!Array.isArray(data.nightLights) || !data.nightLights.every(isNightLight)))
    )
        return null;
    return {
        boxes: data.boxes,
        spawn: data.spawn,
        overview: data.overview,
        ...(data.solids !== undefined ? { solids: data.solids as CollisionSolid[] } : {}),
        ...(data.vehicleSpawn !== undefined
            ? { vehicleSpawn: data.vehicleSpawn as [number, number, number, number] }
            : {}),
        ...(data.nightLights !== undefined
            ? { nightLights: data.nightLights as NightLightAnchor[] }
            : {}),
    };
}

export const EYE_HEIGHT = 1.7;
export const PLAYER_RADIUS = 0.35;
export const WALK_SPEED = 7;
export const RUN_SPEED = 12;

export function movementDelta(
    forward: number,
    strafe: number,
    yaw: number,
    distance: number,
): HorizontalPoint {
    const length = Math.max(1, Math.hypot(forward, strafe));
    const f = forward / length;
    const s = strafe / length;
    return {
        x: (s * Math.cos(yaw) - f * Math.sin(yaw)) * distance,
        z: (-s * Math.sin(yaw) - f * Math.cos(yaw)) * distance,
    };
}

export function playerCollides(
    point: HorizontalPoint,
    groundY: number,
    boxes: readonly CollisionBox[],
): boolean {
    return boxes.some(
        (box) =>
            groundY + EYE_HEIGHT > box.minY + 0.05 &&
            groundY + 0.15 < box.maxY &&
            point.x + PLAYER_RADIUS > box.minX &&
            point.x - PLAYER_RADIUS < box.maxX &&
            point.z + PLAYER_RADIUS > box.minZ &&
            point.z - PLAYER_RADIUS < box.maxZ,
    );
}

export function canStepTo(currentGround: number, nextGround: number): boolean {
    const height = nextGround - currentGround;
    return Number.isFinite(nextGround) && height <= 0.45 && height >= -1.2;
}
