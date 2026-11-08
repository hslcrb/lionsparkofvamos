import test from 'node:test';
import assert from 'node:assert/strict';
import { isCinemaSwipe } from '../src/gesture';

test('a deliberate left swipe enters the cinema without hijacking vertical scrolling', () => {
    assert.equal(isCinemaSwipe({ x: 220, y: 100 }, { x: 110, y: 115 }), true);
    assert.equal(isCinemaSwipe({ x: 220, y: 100 }, { x: 190, y: 105 }), false);
    assert.equal(isCinemaSwipe({ x: 220, y: 100 }, { x: 160, y: 230 }), false);
    assert.equal(isCinemaSwipe({ x: 110, y: 100 }, { x: 220, y: 100 }), false);
});
