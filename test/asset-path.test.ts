import assert from 'node:assert/strict';
import test from 'node:test';
import { assetPath } from '../src/asset-path';

test('asset paths stay absolute by default', () => {
    assert.equal(assetPath('/models/lionspark.glb'), '/models/lionspark.glb');
});

test('relative or external values are untouched', () => {
    assert.equal(assetPath('https://example.com/a.glb'), 'https://example.com/a.glb');
});
