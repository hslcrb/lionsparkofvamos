import test from 'node:test';
import assert from 'node:assert/strict';
import {
    canStepTo,
    movementDelta,
    parseCollisionData,
    playerCollides,
    type CollisionBox,
} from '../src/features/lionspark/navigation';

test('walking follows the view direction and diagonal input does not run faster', () => {
    assert.deepEqual(movementDelta(1, 0, 0, 5), { x: 0, z: -5 });
    const turn = movementDelta(1, 0, Math.PI / 2, 5);
    assert.ok(Math.abs(turn.x + 5) < 1e-10);
    assert.ok(Math.abs(turn.z) < 1e-10);
    const diagonal = movementDelta(1, 1, 0, 5);
    assert.ok(Math.abs(Math.hypot(diagonal.x, diagonal.z) - 5) < 1e-10);
});

test('ground movement rejects large steps and drops but allows ramps', () => {
    assert.equal(canStepTo(0, 0.3), true);
    assert.equal(canStepTo(0, 0.5), false);
    assert.equal(canStepTo(0, -2), false);
    assert.equal(canStepTo(0, NaN), false);
});

test('body collision stops at walls while allowing passage under high canopies', () => {
    const box: CollisionBox = { minX: 1, maxX: 2, minY: 0, maxY: 4, minZ: -1, maxZ: 1 };
    assert.equal(playerCollides({ x: 0.8, z: 0 }, 0, [box]), true);
    assert.equal(playerCollides({ x: 0, z: 0 }, 0, [box]), false);
    assert.equal(playerCollides({ x: 1.5, z: 0 }, 0, [{ ...box, minY: 4, maxY: 6 }]), false);
});

test('collision exports reject invalid bounds and preserve individual loose components', () => {
    const boxes: CollisionBox[] = [
        { minX: -10, maxX: -5, minY: 0, maxY: 4, minZ: -1, maxZ: 1 },
        { minX: 5, maxX: 10, minY: 0, maxY: 4, minZ: -1, maxZ: 1 },
    ];
    const data = { boxes, spawn: [0, 1.7, 165], overview: [255, 240, 340] };
    const parsed = parseCollisionData(data);
    assert.deepEqual(parsed?.boxes, boxes);
    assert.equal(playerCollides({ x: 0, z: 0 }, 0, parsed?.boxes ?? []), false);
    assert.equal(parseCollisionData({ ...data, boxes: [{ ...boxes[0], minX: 20 }] }), null);
    assert.equal(parseCollisionData({ ...data, spawn: [0, NaN, 0] }), null);
});

// 충돌 자료 검증 / Collision data validation
test('oriented solids and vehicle spawn survive parsing without accepting malformed bounds', () => {
    const solid = { cx: 3, cz: -4, hx: 0.15, hz: 2, yaw: Math.PI / 4, minY: 0, maxY: 3 };
    const data = {
        boxes: [],
        solids: [solid],
        spawn: [0, 1.7, 165],
        overview: [255, 240, 340],
        vehicleSpawn: [0, 0, 155, Math.PI],
        nightLights: [{ position: [1, 6, 2], target: [1, 0, 2], kind: 'road' }],
    };
    assert.deepEqual(parseCollisionData(data), data);
    assert.equal(parseCollisionData({ ...data, solids: [{ ...solid, hx: -1 }] }), null);
    assert.equal(parseCollisionData({ ...data, solids: [{ ...solid, yaw: NaN }] }), null);
    assert.equal(parseCollisionData({ ...data, solids: [{ ...solid, minY: 4 }] }), null);
    assert.equal(parseCollisionData({ ...data, vehicleSpawn: [0, 0, 0] }), null);
    assert.equal(parseCollisionData({ ...data, nightLights: [{ position: [1, 2, 3] }] }), null);
});
