import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { GroundIndex } from '../src/features/lionspark/ground-index';

// 실제 표면 시험 도구 / Real surface test fixtures
function floor(width: number, depth: number, y = 0): THREE.Mesh {
    const mesh = new THREE.Mesh(
        new THREE.PlaneGeometry(width, depth).rotateX(-Math.PI / 2),
        new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }),
    );
    mesh.position.y = y;
    return mesh;
}

function rayHeight(meshes: THREE.Mesh[], x: number, z: number, eyeY: number): number | null {
    const ray = new THREE.Raycaster(
        new THREE.Vector3(x, eyeY + 0.75, z),
        new THREE.Vector3(0, -1, 0),
        0,
        6,
    );
    for (const mesh of meshes) mesh.updateWorldMatrix(true, false);
    return ray.intersectObjects(meshes, false)[0]?.point.y ?? null;
}

// 계단과 경사면 / Stairs and sloped surfaces
test('indexed ground follows individual stair tops instead of their combined bounds', () => {
    const stairs = [0, 1, 2, 3].map((step) => {
        const mesh = new THREE.Mesh(new THREE.BoxGeometry(4, 0.2, 1));
        mesh.position.set(0, step * 0.2, step);
        return mesh;
    });
    const index = new GroundIndex(stairs);
    assert.ok(Math.abs(index.getHeight(0, 0, 1.7)! - 0.1) < 1e-6);
    assert.ok(Math.abs(index.getHeight(0, 2, 2.1)! - 0.5) < 1e-6);
    assert.equal(index.getHeight(3, 2, 2.1), null);
});

test('world transforms and ramp interpolation match downward raycasts', () => {
    const parent = new THREE.Group();
    parent.position.set(15, 0.7, -9);
    parent.rotation.y = 0.4;
    const ramp = floor(6, 8);
    ramp.rotation.x = 0.2;
    ramp.scale.set(1.2, 1, 0.8);
    parent.add(ramp);
    const index = new GroundIndex([ramp], 2);
    for (const [x, z] of [
        [15, -9],
        [16, -8],
        [14, -10],
    ]) {
        const expected = rayHeight([ramp], x!, z!, 2.4);
        const actual = index.getHeight(x!, z!, 2.4);
        assert.ok(expected !== null && actual !== null);
        assert.ok(Math.abs(actual - expected) < 1e-6);
    }
});

// 높이 대역과 외곽 / Height band and surface boundaries
test('stacked floors choose the highest surface inside the original six meter ray band', () => {
    const index = new GroundIndex([floor(8, 8, 0), floor(8, 8, 3), floor(8, 8, 10)]);
    assert.equal(index.getHeight(0, 0, 1.7), 0);
    assert.equal(index.getHeight(0, 0, 3), 3);
    assert.equal(index.getHeight(0, 0, 7), 3);
    assert.equal(index.getHeight(0, 0, 9.5), 10);
    assert.equal(index.getHeight(0, 0, 20), null);
    assert.equal(index.getHeight(0, 0, -2), null);
});

test('triangular ground does not fill its empty AABB half or extend past the walkable edge', () => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
        'position',
        new THREE.Float32BufferAttribute([0, 0, 0, 8, 0, 0, 0, 0, 8], 3),
    );
    const index = new GroundIndex([new THREE.Mesh(geometry)], 2);
    assert.equal(index.getHeight(1, 1, 1.7), 0);
    assert.equal(index.getHeight(6, 6, 1.7), null);
    assert.equal(index.getHeight(0, 4, 1.7), 0);
    assert.equal(index.getHeight(-0.01, 4, 1.7), null);
});

test('giant terrain and negative tile boundaries remain queryable without filling empty space', () => {
    const terrain = floor(1400, 1400, -0.1);
    const landing = floor(3, 3, 0.6);
    landing.position.set(-12, 0.6, -12);
    const index = new GroundIndex([terrain, landing]);
    assert.equal(index.getHeight(-12, -12, 1.7), 0.6);
    assert.ok(Math.abs(index.getHeight(699, 699, 1.7)! + 0.1) < 1e-6);
    assert.equal(index.getHeight(701, 699, 1.7), null);
});

test('vertical walls, degenerate triangles and invalid coordinates cannot become walkable floors', () => {
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(4, 8));
    const degenerate = new THREE.BufferGeometry();
    degenerate.setAttribute(
        'position',
        new THREE.Float32BufferAttribute([0, 0, 0, 0, 0, 0, 1, 0, 0], 3),
    );
    const index = new GroundIndex([wall, new THREE.Mesh(degenerate)]);
    assert.equal(index.getHeight(0, 0, 1.7), null);
    assert.equal(index.getHeight(NaN, 0, 1.7), null);
    assert.equal(index.getHeight(0, Infinity, 1.7), null);
});
