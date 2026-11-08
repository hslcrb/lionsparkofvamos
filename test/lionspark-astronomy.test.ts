import test from 'node:test';
import assert from 'node:assert/strict';
import {
    previewEpoch,
    sampleCelestial,
    type CelestialDirection,
} from '../src/features/lionspark/astronomy';

const HOUR = 3_600_000;
const radians = (degrees: number) => (degrees * Math.PI) / 180;
const length = (direction: CelestialDirection) => Math.hypot(direction.x, direction.y, direction.z);
const dot = (a: CelestialDirection, b: CelestialDirection) => a.x * b.x + a.y * b.y + a.z * b.z;
const kstHour = (epochMs: number) =>
    ((((epochMs + 9 * HOUR) % (24 * HOUR)) + 24 * HOUR) % (24 * HOUR)) / HOUR;

test('November previews use the same Korean date and the actual eastern and western horizons', () => {
    const epoch = Date.parse('2026-11-03T23:55:00+09:00');
    const sunrise = previewEpoch(epoch, 'sunrise');
    const sunset = previewEpoch(epoch, 'sunset');
    assert.ok(kstHour(sunrise) > 6 && kstHour(sunrise) < 8);
    assert.ok(kstHour(sunset) > 16 && kstHour(sunset) < 19);
    assert.equal(new Date(sunrise + 9 * HOUR).toISOString().slice(0, 10), '2026-11-03');
    assert.equal(new Date(sunset + 9 * HOUR).toISOString().slice(0, 10), '2026-11-03');
    const dawn = sampleCelestial(sunrise);
    const dusk = sampleCelestial(sunset);
    assert.ok(Math.abs(dawn.sunAltitudeRadians - radians(0.4)) < 0.00001);
    assert.ok(Math.abs(dusk.sunAltitudeRadians - radians(-0.4)) < 0.00001);
    assert.ok(dawn.sunDirection.x > 0.6);
    assert.ok(dusk.sunDirection.x < -0.6);
    assert.ok(sampleCelestial(sunrise + 60_000).sunAltitudeRadians > dawn.sunAltitudeRadians);
    assert.ok(sampleCelestial(sunset + 60_000).sunAltitudeRadians < dusk.sunAltitudeRadians);
});

test('Daegu summer daylight is longer and the noon sun is higher than in winter', () => {
    const summer = Date.parse('2026-06-21T12:00:00+09:00');
    const winter = Date.parse('2026-12-21T12:00:00+09:00');
    const dayLength = (epoch: number) =>
        previewEpoch(epoch, 'sunset') - previewEpoch(epoch, 'sunrise');
    assert.ok(dayLength(summer) > 14 * HOUR);
    assert.ok(dayLength(winter) < 10 * HOUR);
    assert.ok(
        sampleCelestial(summer).sunAltitudeRadians >
            sampleCelestial(winter).sunAltitudeRadians + radians(40),
    );
    assert.ok(sampleCelestial(summer).sunDirection.z > 0);
});

test('sun, moon, and equatorial axes are normalized and continuous across Korean midnight', () => {
    const midnight = Date.parse('2026-11-04T00:00:00+09:00');
    const before = sampleCelestial(midnight - 1000);
    const after = sampleCelestial(midnight + 1000);
    for (const key of ['sunDirection', 'moonDirection'] as const) {
        assert.ok(Math.abs(length(before[key]) - 1) < 1e-12);
        assert.ok(Math.abs(length(after[key]) - 1) < 1e-12);
        assert.ok(dot(before[key], after[key]) > 0.9999999);
    }
    const { ra0, ra90, northPole } = after.equatorialBasis;
    for (const axis of [ra0, ra90, northPole]) assert.ok(Math.abs(length(axis) - 1) < 1e-12);
    assert.ok(Math.abs(dot(ra0, ra90)) < 1e-12);
    assert.ok(Math.abs(dot(ra0, northPole)) < 1e-12);
    assert.ok(Math.abs(dot(ra90, northPole)) < 1e-12);
    assert.ok(Math.abs(after.siderealRadians - before.siderealRadians) < 0.001);
    assert.ok(Math.abs(northPole.y - Math.sin(radians(35.84))) < 1e-12);
    assert.ok(northPole.z < 0);
});

test('the stellar sky follows sidereal rotation rather than repeating at solar midnight', () => {
    const epoch = Date.parse('2026-11-03T21:00:00+09:00');
    const now = sampleCelestial(epoch);
    const nextDay = sampleCelestial(epoch + 24 * HOUR);
    const siderealDay = sampleCelestial(epoch + 86_164_090.5);
    assert.ok(dot(now.equatorialBasis.ra0, nextDay.equatorialBasis.ra0) < 0.9999);
    assert.ok(dot(now.equatorialBasis.ra0, siderealDay.equatorialBasis.ra0) > 0.999999999);
});

test('moon illumination stays bounded and distinguishes the November new and full moon', () => {
    for (let day = 1; day <= 30; day += 1) {
        const sample = sampleCelestial(
            Date.parse(`2026-11-${String(day).padStart(2, '0')}T21:00:00+09:00`),
        );
        assert.ok(sample.moonIllumination >= 0 && sample.moonIllumination <= 1);
        assert.ok(Number.isFinite(sample.moonAltitudeRadians));
        assert.ok(sample.moonPhaseAngleRadians >= 0 && sample.moonPhaseAngleRadians <= Math.PI);
    }
    assert.ok(sampleCelestial(Date.parse('2026-11-09T12:00:00Z')).moonIllumination < 0.02);
    assert.ok(sampleCelestial(Date.parse('2026-11-24T12:00:00Z')).moonIllumination > 0.98);
});
