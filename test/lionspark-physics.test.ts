import test from 'node:test';
import assert from 'node:assert/strict';
import type { CollisionSolid } from '../src/features/lionspark/navigation';
import {
    findVehicleExit,
    movePlayer,
    simulateVehicle,
    SolidIndex,
    type VehicleState,
} from '../src/features/lionspark/physics';

// 보행 장애물과 높이 / Walking obstacles and clearance
test('walkers stop at trunks, benches and parked cars while clearing an overhead canopy', () => {
    const solids: CollisionSolid[] = [
        { cx: 0, cz: 0, hx: 0.2, hz: 0.2, yaw: 0, minY: 0, maxY: 6 },
        { cx: 3, cz: 0, hx: 1, hz: 0.3, yaw: Math.PI / 4, minY: 0.4, maxY: 0.9 },
        { cx: 7, cz: 0, hx: 0.95, hz: 2.25, yaw: 0, minY: 0.15, maxY: 1.6 },
        { cx: 11, cz: 0, hx: 2, hz: 2, yaw: 0, minY: 2.4, maxY: 5 },
    ];
    const index = new SolidIndex(solids);
    assert.equal(index.collidesCircle(0.4, 0, 0), true);
    assert.equal(index.collidesCircle(3, 0, 0), true);
    assert.equal(index.collidesCircle(7, 0, 0), true);
    assert.equal(index.collidesCircle(11, 0, 0), false);
    assert.equal(index.collidesCircle(11, 0, 1), true);
    assert.equal(index.collidesCircle(0.5, 0.5, 0), false);
});

test('solid cells span boundaries and rotated thin walls retain their open corners', () => {
    const index = new SolidIndex([
        { cx: 8, cz: 0, hx: 0.05, hz: 8, yaw: Math.PI / 4, minY: 0, maxY: 3 },
    ]);
    assert.equal(index.collidesCircle(8, 0, 0), true);
    assert.equal(index.collidesCircle(13, -5, 0), true);
    assert.equal(index.collidesCircle(13, 5, 0), false);
});

test('new solids replace legacy batch boxes instead of enclosing gaps between objects', () => {
    const index = new SolidIndex({
        boxes: [{ minX: -10, maxX: 10, minY: 0, maxY: 10, minZ: -10, maxZ: 10 }],
        solids: [],
    });
    assert.equal(index.collidesCircle(0, 0, 0), false);
    const legacy = new SolidIndex({
        boxes: [{ minX: -1, maxX: 1, minY: 0, maxY: 10, minZ: -1, maxZ: 1 }],
    });
    assert.equal(legacy.collidesCircle(0, 0, 0), true);
});

test('running cannot tunnel through a thin wall even when a frame spans the entire wall', () => {
    const index = new SolidIndex([{ cx: 0, cz: 0, hx: 0.01, hz: 10, yaw: 0, minY: 0, maxY: 3 }]);
    const end = movePlayer(
        { x: -2, z: 0 },
        { x: 6, z: 1 },
        (point) => !index.collidesCircle(point.x, point.z, 0),
    );
    assert.ok(end.x < -0.35, `walker crossed the wall to ${end.x}`);
    assert.ok(end.z > 0.8, 'walker should slide along a blocked wall');
});

// 차량 외곽과 운동 / Vehicle footprint and motion
test('vehicle footprint includes the actual mirror overhang', () => {
    const state: VehicleState = { x: 0, z: 0, yaw: 0, speed: 0 };
    const mirrorWall = new SolidIndex([
        { cx: 1.1, cz: -0.64, hx: 0.01, hz: 0.3, yaw: 0, minY: 0.9, maxY: 1.2 },
    ]);
    assert.equal(mirrorWall.collidesVehicle(state, 0), true);
});

test('vehicle footprint includes the actual front plate overhang', () => {
    const state: VehicleState = { x: 0, z: 0, yaw: 0, speed: 0 };
    const plateWall = new SolidIndex([
        { cx: 0, cz: -2.28, hx: 0.3, hz: 0.01, yaw: 0, minY: 0.3, maxY: 0.7 },
    ]);
    assert.equal(plateWall.collidesVehicle(state, 0), true);
});

test('vehicle collision catches a rotated corner that its center and axle points miss', () => {
    const index = new SolidIndex([
        { cx: 2, cz: 1.15, hx: 0.12, hz: 0.12, yaw: 0, minY: 0, maxY: 1 },
    ]);
    const state: VehicleState = { x: 0, z: 0, yaw: Math.PI / 4, speed: 0 };
    assert.equal(index.collidesCircle(0, 0, 0), false);
    assert.equal(index.collidesVehicle(state, 0), true);
    assert.equal(index.collidesVehicle({ ...state, yaw: 0 }, 0), false);
    assert.equal(index.collidesVehicle(state, 2), false);
});

test('driving at road speed stops before a thin wall without teleporting through it', () => {
    const index = new SolidIndex([{ cx: 0, cz: 0, hx: 10, hz: 0.01, yaw: 0, minY: 0, maxY: 3 }]);
    const end = simulateVehicle(
        { x: 0, z: 8, yaw: 0, speed: 16 },
        { throttle: 1, steer: 0, brake: false },
        1,
        (candidate) => !index.collidesVehicle(candidate, 0),
    );
    assert.ok(end.z > 2.25, `car crossed the wall to ${end.z}`);
    assert.equal(end.speed, 0);
    assert.equal(index.collidesVehicle(end, 0), false);
});

test('steering cannot rotate a moving vehicle through an adjacent obstacle', () => {
    const index = new SolidIndex([
        { cx: 1.35, cz: 0.5, hx: 0.12, hz: 1.5, yaw: 0, minY: 0, maxY: 2 },
    ]);
    let state: VehicleState = { x: 0, z: 0, yaw: 0, speed: 0 };
    for (let step = 0; step < 90; step++) {
        state = simulateVehicle(
            state,
            { throttle: 1, steer: 1, brake: false },
            1 / 60,
            (next) => !index.collidesVehicle(next, 0),
        );
        assert.equal(index.collidesVehicle(state, 0), false);
    }
    const parked = simulateVehicle(
        { x: 0, z: 0, yaw: 0, speed: 0 },
        { throttle: 0, steer: 1, brake: false },
        1,
        () => true,
    );
    assert.equal(parked.yaw, 0);
});

test('accelerator, brake and reverse preserve a controllable road speed', () => {
    let state: VehicleState = { x: 0, z: 0, yaw: 0, speed: 0 };
    for (let step = 0; step < 600; step++)
        state = simulateVehicle(state, { throttle: 1, steer: 0, brake: false }, 1 / 60, () => true);
    assert.ok(state.speed > 15 && state.speed < 17);
    assert.ok(state.z < -70);
    const beforeBrake = state.speed;
    state = simulateVehicle(state, { throttle: 1, steer: 0, brake: true }, 0.5, () => true);
    assert.ok(state.speed < beforeBrake - 3);
    for (let step = 0; step < 240; step++)
        state = simulateVehicle(
            state,
            { throttle: -1, steer: 0, brake: false },
            1 / 60,
            () => true,
        );
    assert.ok(state.speed < -1 && state.speed >= -5.6);
});

test('an exit uses a clear side and stays inside when every candidate is blocked', () => {
    const state: VehicleState = { x: 0, z: 0, yaw: 0, speed: 0 };
    const index = new SolidIndex([{ cx: -1.1, cz: 0, hx: 0.03, hz: 10, yaw: 0, minY: 0, maxY: 3 }]);
    const exit = findVehicleExit(state, 0, (point) => !index.collidesCircle(point.x, point.z, 0));
    assert.ok(exit && exit.x > 1.4);
    assert.equal(
        findVehicleExit(state, 0, () => false),
        null,
    );
});

test('exiting cannot teleport across a thin fence surrounding the vehicle', () => {
    const index = new SolidIndex([
        { cx: -1.1, cz: 0, hx: 0.03, hz: 2.4, yaw: 0, minY: 0, maxY: 3 },
        { cx: 1.1, cz: 0, hx: 0.03, hz: 2.4, yaw: 0, minY: 0, maxY: 3 },
        { cx: 0, cz: -2.4, hx: 1.1, hz: 0.03, yaw: 0, minY: 0, maxY: 3 },
        { cx: 0, cz: 2.4, hx: 1.1, hz: 0.03, yaw: 0, minY: 0, maxY: 3 },
    ]);
    assert.equal(
        findVehicleExit(
            { x: 0, z: 0, yaw: 0, speed: 0 },
            0,
            (point) => !index.collidesCircle(point.x, point.z, 0),
        ),
        null,
    );
});
