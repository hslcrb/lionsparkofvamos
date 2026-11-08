import test from 'node:test';
import assert from 'node:assert/strict';
import { applyRoomMessage, parseServerMessage, parseClientMessage } from '../src/room';

test('room events update shared count and presence without erasing the other value', () => {
    const state = { cheers: 12, online: 3 };
    assert.deepEqual(applyRoomMessage(state, { type: 'cheer', cheers: 13, online: 4 }), {
        cheers: 13,
        online: 4,
    });
    assert.deepEqual(applyRoomMessage(state, { type: 'presence', online: 2 }), {
        cheers: 12,
        online: 2,
    });
});

test('invalid room values do not corrupt displayed totals', () => {
    const state = { cheers: 12, online: 3 };
    assert.deepEqual(applyRoomMessage(state, { type: 'state', cheers: -1, online: 'many' }), state);
});

test('untrusted messages cannot select invalid moves or overwrite room state', () => {
    for (const raw of [
        null,
        [],
        7,
        { type: 'dance', dance: 'unknown', online: 2 },
        { type: 'state', cheers: Infinity, online: 2 },
    ]) {
        assert.equal(parseServerMessage(raw), null);
    }
    assert.equal(parseClientMessage({ type: 'dance', dance: '__proto__' }), null);
    assert.deepEqual(parseClientMessage({ type: 'dance', dance: 'bounce' }), {
        type: 'dance',
        dance: 'bounce',
    });
    assert.deepEqual(applyRoomMessage({ cheers: 1, online: 2 }, null), { cheers: 1, online: 2 });
});
