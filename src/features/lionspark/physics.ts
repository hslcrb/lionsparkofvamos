import {
    EYE_HEIGHT,
    PLAYER_RADIUS,
    type CollisionBox,
    type CollisionSolid,
    type HorizontalPoint,
} from './navigation';

// 차량 규격과 입력 / Vehicle dimensions and controls
export const VEHICLE_WIDTH = 2.26;
export const VEHICLE_LENGTH = 4.58;
export const VEHICLE_HEIGHT = 1.5;
export const VEHICLE_MAX_SPEED = 60 / 3.6;
export const VEHICLE_MAX_REVERSE = 20 / 3.6;

export interface VehicleState extends HorizontalPoint {
    yaw: number;
    speed: number;
    steering?: number;
}

export interface VehicleInput {
    throttle: number;
    steer: number;
    brake: boolean;
}

interface IndexedSolid extends CollisionSolid {
    cos: number;
    sin: number;
    minX: number;
    maxX: number;
    minZ: number;
    maxZ: number;
}

interface SolidData {
    boxes?: readonly CollisionBox[];
    solids?: readonly CollisionSolid[];
}

function prepareSolid(solid: CollisionSolid): IndexedSolid {
    const cos = Math.cos(solid.yaw);
    const sin = Math.sin(solid.yaw);
    const extentX = Math.abs(cos) * solid.hx + Math.abs(sin) * solid.hz;
    const extentZ = Math.abs(sin) * solid.hx + Math.abs(cos) * solid.hz;
    return {
        ...solid,
        cos,
        sin,
        minX: solid.cx - extentX,
        maxX: solid.cx + extentX,
        minZ: solid.cz - extentZ,
        maxZ: solid.cz + extentZ,
    };
}

function legacySolid(box: CollisionBox): CollisionSolid {
    return {
        cx: (box.minX + box.maxX) / 2,
        cz: (box.minZ + box.maxZ) / 2,
        hx: (box.maxX - box.minX) / 2,
        hz: (box.maxZ - box.minZ) / 2,
        yaw: 0,
        minY: box.minY,
        maxY: box.maxY,
    };
}

// 정밀 외곽 검사 / Precise footprint tests
function verticalOverlap(solid: CollisionSolid, groundY: number, height: number): boolean {
    return groundY + height > solid.minY + 0.02 && groundY + 0.05 < solid.maxY;
}

function rectanglesOverlap(a: IndexedSolid, b: IndexedSolid): boolean {
    const dx = b.cx - a.cx;
    const dz = b.cz - a.cz;
    const axes = [
        [a.cos, a.sin],
        [-a.sin, a.cos],
        [b.cos, b.sin],
        [-b.sin, b.cos],
    ] as const;
    for (const [ax, az] of axes) {
        const aRadius =
            a.hx * Math.abs(ax * a.cos + az * a.sin) + a.hz * Math.abs(-ax * a.sin + az * a.cos);
        const bRadius =
            b.hx * Math.abs(ax * b.cos + az * b.sin) + b.hz * Math.abs(-ax * b.sin + az * b.cos);
        if (Math.abs(dx * ax + dz * az) >= aRadius + bRadius - 1e-8) return false;
    }
    return true;
}

// 공간 해시: 인접 셀만 검사 / Spatial hash: inspect nearby cells only
export class SolidIndex {
    private readonly solids: IndexedSolid[];
    private readonly buckets = new Map<string, number[]>();
    private readonly oversized: number[] = [];
    private readonly visited: Uint32Array;
    private stamp = 0;
    private readonly cellSize: number;

    constructor(data: SolidData | readonly CollisionSolid[], cellSize = 8) {
        this.cellSize = Number.isFinite(cellSize) && cellSize > 0 ? cellSize : 8;
        const source: SolidData = Array.isArray(data) ? { solids: data } : (data as SolidData);
        this.solids = (source.solids ?? source.boxes?.map(legacySolid) ?? []).map(prepareSolid);
        this.visited = new Uint32Array(this.solids.length);
        this.solids.forEach((solid, index) => {
            const minX = Math.floor(solid.minX / this.cellSize);
            const maxX = Math.floor(solid.maxX / this.cellSize);
            const minZ = Math.floor(solid.minZ / this.cellSize);
            const maxZ = Math.floor(solid.maxZ / this.cellSize);
            if ((maxX - minX + 1) * (maxZ - minZ + 1) > 4096) {
                this.oversized.push(index);
                return;
            }
            for (let x = minX; x <= maxX; x++) {
                for (let z = minZ; z <= maxZ; z++) {
                    const key = `${x}:${z}`;
                    const bucket = this.buckets.get(key);
                    if (bucket) bucket.push(index);
                    else this.buckets.set(key, [index]);
                }
            }
        });
    }

    private anyNearby(
        minX: number,
        maxX: number,
        minZ: number,
        maxZ: number,
        overlaps: (solid: IndexedSolid) => boolean,
    ): boolean {
        this.stamp = (this.stamp + 1) >>> 0;
        if (this.stamp === 0) {
            this.visited.fill(0);
            this.stamp = 1;
        }
        const test = (index: number): boolean => {
            if (this.visited[index] === this.stamp) return false;
            this.visited[index] = this.stamp;
            const solid = this.solids[index]!;
            return (
                solid.maxX >= minX &&
                solid.minX <= maxX &&
                solid.maxZ >= minZ &&
                solid.minZ <= maxZ &&
                overlaps(solid)
            );
        };
        for (const index of this.oversized) if (test(index)) return true;
        for (let x = Math.floor(minX / this.cellSize); x <= Math.floor(maxX / this.cellSize); x++) {
            for (
                let z = Math.floor(minZ / this.cellSize);
                z <= Math.floor(maxZ / this.cellSize);
                z++
            ) {
                const bucket = this.buckets.get(`${x}:${z}`);
                if (bucket) for (const index of bucket) if (test(index)) return true;
            }
        }
        return false;
    }

    collidesCircle(
        x: number,
        z: number,
        groundY: number,
        radius = PLAYER_RADIUS,
        height = EYE_HEIGHT,
    ): boolean {
        if (![x, z, groundY, radius, height].every(Number.isFinite) || radius < 0 || height <= 0)
            return true;
        return this.anyNearby(x - radius, x + radius, z - radius, z + radius, (solid) => {
            if (!verticalOverlap(solid, groundY, height)) return false;
            const dx = x - solid.cx;
            const dz = z - solid.cz;
            const localX = dx * solid.cos + dz * solid.sin;
            const localZ = -dx * solid.sin + dz * solid.cos;
            const closestX = Math.max(-solid.hx, Math.min(solid.hx, localX));
            const closestZ = Math.max(-solid.hz, Math.min(solid.hz, localZ));
            return (localX - closestX) ** 2 + (localZ - closestZ) ** 2 < radius * radius;
        });
    }

    collidesVehicle(state: VehicleState, groundY: number): boolean {
        if (![state.x, state.z, state.yaw, groundY].every(Number.isFinite)) return true;
        const body = prepareSolid({
            cx: state.x,
            cz: state.z,
            hx: VEHICLE_WIDTH / 2,
            hz: VEHICLE_LENGTH / 2,
            yaw: -state.yaw,
            minY: groundY,
            maxY: groundY + VEHICLE_HEIGHT,
        });
        return this.anyNearby(
            body.minX,
            body.maxX,
            body.minZ,
            body.maxZ,
            (solid) =>
                verticalOverlap(solid, groundY, VEHICLE_HEIGHT) && rectanglesOverlap(body, solid),
        );
    }
}

// 보행 경로 분할과 벽 미끄러짐 / Walking substeps and wall sliding
export function movePlayer(
    current: HorizontalPoint,
    delta: HorizontalPoint,
    canOccupy: (point: HorizontalPoint) => boolean,
): HorizontalPoint {
    let result = { ...current };
    if (![current.x, current.z, delta.x, delta.z].every(Number.isFinite)) return result;
    const count = Math.max(1, Math.ceil(Math.hypot(delta.x, delta.z) / 0.15));
    const dx = delta.x / count;
    const dz = delta.z / count;
    for (let step = 0; step < count; step++) {
        const next = { x: result.x + dx, z: result.z + dz };
        if (canOccupy(next)) result = next;
        else {
            const nextX = { x: result.x + dx, z: result.z };
            if (dx !== 0 && canOccupy(nextX)) result = nextX;
            const nextZ = { x: result.x, z: result.z + dz };
            if (dz !== 0 && canOccupy(nextZ)) result = nextZ;
        }
    }
    return result;
}

function approach(value: number, target: number, change: number): number {
    return value < target ? Math.min(value + change, target) : Math.max(value - change, target);
}

// 자전거 모델과 충돌 정지 / Bicycle steering model and collision stops
export function simulateVehicle(
    state: VehicleState,
    input: VehicleInput,
    dt: number,
    canOccupy: (state: VehicleState) => boolean,
): VehicleState {
    let result = { ...state, steering: state.steering ?? 0 };
    if (!Number.isFinite(dt) || dt <= 0) return result;
    const duration = Math.min(dt, 1);
    const throttle = Number.isFinite(input.throttle)
        ? Math.max(-1, Math.min(1, input.throttle))
        : 0;
    const steer = Number.isFinite(input.steer) ? Math.max(-1, Math.min(1, input.steer)) : 0;
    const travelBound = (Math.abs(state.speed) + 5 * duration) * duration;
    const count = Math.max(1, Math.ceil(duration / 0.02), Math.ceil((travelBound * 1.7) / 0.1));
    const seconds = duration / count;
    for (let step = 0; step < count; step++) {
        const steering = approach(result.steering, steer * 0.5, seconds * 1.6);
        let speed = result.speed;
        if (input.brake) speed = approach(speed, 0, 11 * seconds);
        else if (throttle !== 0) {
            if (speed * throttle < -0.05) speed = approach(speed, 0, 8 * seconds);
            else speed += throttle * (throttle > 0 ? 4.5 : 3) * seconds;
        } else speed = approach(speed, 0, 0.8 * seconds);
        speed = approach(speed, 0, (0.12 + speed * speed * 0.005) * seconds);
        speed = Math.max(-VEHICLE_MAX_REVERSE, Math.min(VEHICLE_MAX_SPEED, speed));
        const yawChange = ((speed * Math.tan(steering)) / 2.65) * seconds;
        const middleYaw = result.yaw + yawChange / 2;
        const next = {
            x: result.x - Math.sin(middleYaw) * speed * seconds,
            z: result.z - Math.cos(middleYaw) * speed * seconds,
            yaw: result.yaw + yawChange,
            speed,
            steering,
        };
        if (!canOccupy(next)) return { ...result, speed: 0, steering };
        result = next;
    }
    return result;
}

// 안전한 하차 위치 / Safe exit candidates
export function findVehicleExit(
    state: VehicleState,
    groundY: number,
    canOccupy: (point: HorizontalPoint, groundY: number) => boolean,
): HorizontalPoint | null {
    const sideDistance = VEHICLE_WIDTH / 2 + PLAYER_RADIUS + 0.35;
    const endDistance = VEHICLE_LENGTH / 2 + PLAYER_RADIUS + 0.4;
    const candidates = [
        [-sideDistance, 0.3],
        [sideDistance, 0.3],
        [-sideDistance, -1.2],
        [sideDistance, -1.2],
        [0, endDistance],
        [0, -endDistance],
        [-sideDistance - 0.05, endDistance - 0.2],
        [sideDistance + 0.05, endDistance - 0.2],
    ] as const;
    for (const [side, forward] of candidates) {
        const point = {
            x: state.x + side * Math.cos(state.yaw) - forward * Math.sin(state.yaw),
            z: state.z - side * Math.sin(state.yaw) - forward * Math.cos(state.yaw),
        };
        const count = Math.ceil(Math.hypot(side, forward) / 0.15);
        let clear = true;
        for (let step = 1; step <= count; step++) {
            if (
                !canOccupy(
                    {
                        x: state.x + ((point.x - state.x) * step) / count,
                        z: state.z + ((point.z - state.z) * step) / count,
                    },
                    groundY,
                )
            ) {
                clear = false;
                break;
            }
        }
        if (clear) return point;
    }
    return null;
}
