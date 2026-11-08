import { Vector3, type Mesh } from 'three';

// 월드 삼각형의 투영과 높이 / World triangle projections and height planes
interface GroundTriangle {
    minX: number;
    maxX: number;
    minZ: number;
    maxZ: number;
    minY: number;
    maxY: number;
    ax: number;
    az: number;
    ac: number;
    bx: number;
    bz: number;
    bc: number;
    heightX: number;
    heightZ: number;
    heightC: number;
}

function projectTriangle(a: Vector3, b: Vector3, c: Vector3): GroundTriangle | null {
    const abx = b.x - a.x;
    const aby = b.y - a.y;
    const abz = b.z - a.z;
    const acx = c.x - a.x;
    const acy = c.y - a.y;
    const acz = c.z - a.z;
    const nx = aby * acz - abz * acy;
    const ny = abz * acx - abx * acz;
    const nz = abx * acy - aby * acx;
    const normalLengthSquared = nx * nx + ny * ny + nz * nz;
    const determinant = -ny;
    if (
        !Number.isFinite(normalLengthSquared) ||
        Math.abs(determinant) < 1e-10 ||
        ny * ny < 0.35 * 0.35 * normalLengthSquared
    )
        return null;
    const ax = (b.z - c.z) / determinant;
    const az = (c.x - b.x) / determinant;
    const ac = -ax * c.x - az * c.z;
    const bx = (c.z - a.z) / determinant;
    const bz = (a.x - c.x) / determinant;
    const bc = -bx * c.x - bz * c.z;
    return {
        minX: Math.min(a.x, b.x, c.x),
        maxX: Math.max(a.x, b.x, c.x),
        minZ: Math.min(a.z, b.z, c.z),
        maxZ: Math.max(a.z, b.z, c.z),
        minY: Math.min(a.y, b.y, c.y),
        maxY: Math.max(a.y, b.y, c.y),
        ax,
        az,
        ac,
        bx,
        bz,
        bc,
        heightX: ax * (a.y - c.y) + bx * (b.y - c.y),
        heightZ: az * (a.y - c.y) + bz * (b.y - c.y),
        heightC: c.y + ac * (a.y - c.y) + bc * (b.y - c.y),
    };
}

// 정적 보행면 공간 인덱스 / Static walkable surface spatial index
export class GroundIndex {
    private readonly triangles: GroundTriangle[] = [];
    private readonly cells = new Map<string, number[]>();
    private readonly oversized: number[] = [];
    private readonly cellSize: number;

    constructor(meshes: readonly Mesh[], cellSize = 12) {
        this.cellSize = Number.isFinite(cellSize) && cellSize > 0 ? cellSize : 12;
        const a = new Vector3();
        const b = new Vector3();
        const c = new Vector3();
        for (const mesh of meshes) {
            mesh.updateWorldMatrix(true, false);
            const positions = mesh.geometry.getAttribute('position');
            if (!positions) continue;
            const indices = mesh.geometry.getIndex();
            const count = indices?.count ?? positions.count;
            const start = Math.max(0, mesh.geometry.drawRange.start);
            const end = Math.min(count, start + mesh.geometry.drawRange.count);
            for (let offset = start; offset + 2 < end; offset += 3) {
                a.fromBufferAttribute(positions, indices?.getX(offset) ?? offset).applyMatrix4(
                    mesh.matrixWorld,
                );
                b.fromBufferAttribute(
                    positions,
                    indices?.getX(offset + 1) ?? offset + 1,
                ).applyMatrix4(mesh.matrixWorld);
                c.fromBufferAttribute(
                    positions,
                    indices?.getX(offset + 2) ?? offset + 2,
                ).applyMatrix4(mesh.matrixWorld);
                const triangle = projectTriangle(a, b, c);
                if (!triangle) continue;
                const index = this.triangles.length;
                this.triangles.push(triangle);
                const minX = Math.floor(triangle.minX / this.cellSize);
                const maxX = Math.floor(triangle.maxX / this.cellSize);
                const minZ = Math.floor(triangle.minZ / this.cellSize);
                const maxZ = Math.floor(triangle.maxZ / this.cellSize);
                if ((maxX - minX + 1) * (maxZ - minZ + 1) > 64) {
                    this.oversized.push(index);
                    continue;
                }
                for (let x = minX; x <= maxX; x++) {
                    for (let z = minZ; z <= maxZ; z++) {
                        const key = `${x}:${z}`;
                        const cell = this.cells.get(key);
                        if (cell) cell.push(index);
                        else this.cells.set(key, [index]);
                    }
                }
            }
        }
    }

    // 기존 하향 광선의 6m 높이 대역 / Original downward ray's six meter height band
    getHeight(x: number, z: number, eyeY: number): number | null {
        if (![x, z, eyeY].every(Number.isFinite)) return null;
        const top = eyeY + 0.75;
        const bottom = top - 6;
        let highest: number | null = null;
        const inspect = (indices: readonly number[]) => {
            for (const index of indices) {
                const triangle = this.triangles[index]!;
                if (
                    x < triangle.minX - 1e-7 ||
                    x > triangle.maxX + 1e-7 ||
                    z < triangle.minZ - 1e-7 ||
                    z > triangle.maxZ + 1e-7 ||
                    triangle.minY > top + 1e-7 ||
                    triangle.maxY < (highest ?? bottom) - 1e-7
                )
                    continue;
                const a = triangle.ax * x + triangle.az * z + triangle.ac;
                const b = triangle.bx * x + triangle.bz * z + triangle.bc;
                if (a < -1e-7 || b < -1e-7 || a + b > 1 + 1e-7) continue;
                const height = triangle.heightX * x + triangle.heightZ * z + triangle.heightC;
                if (height > top + 1e-7 || height < bottom - 1e-7) continue;
                if (highest === null || height > highest) highest = height;
            }
        };
        const cell = this.cells.get(
            `${Math.floor(x / this.cellSize)}:${Math.floor(z / this.cellSize)}`,
        );
        if (cell) inspect(cell);
        inspect(this.oversized);
        return highest;
    }
}
