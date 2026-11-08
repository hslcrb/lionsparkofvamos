/**
 * Visual ephemeris for Daegu Samsung Lions Park, using UTC epochs throughout.
 * Solar coordinates follow the Meeus equations described by NOAA:
 * https://gml.noaa.gov/grad/solcalc/calcdetails.html
 * The Moon uses the dominant periodic terms, sufficient for its sky position
 * and visible phase; this is a scene clock rather than an observing almanac.
 * Elevations are geometric, without terrain or atmospheric refraction.
 */
export const LIONSPARK_COORDINATES = { latitude: 35.84, longitude: 128.68 } as const;

export interface CelestialDirection {
    x: number;
    y: number;
    z: number;
}

export interface EquatorialBasis {
    ra0: CelestialDirection;
    ra90: CelestialDirection;
    northPole: CelestialDirection;
}

export interface CelestialSample {
    sunDirection: CelestialDirection;
    sunAltitudeRadians: number;
    /** Azimuth clockwise from geographic north, in [0, 2π). */
    sunAzimuthRadians: number;
    moonDirection: CelestialDirection;
    moonAltitudeRadians: number;
    moonIllumination: number;
    /** Sun–Moon–observer angle: 0 at full Moon, π at new Moon. */
    moonPhaseAngleRadians: number;
    /** Local mean sidereal angle, in [0, 2π). */
    siderealRadians: number;
    equatorialBasis: EquatorialBasis;
}

const DEG = Math.PI / 180;
const TAU = 2 * Math.PI;
const DAY_MS = 86_400_000;
const KST_OFFSET_MS = 9 * 3_600_000;
const LATITUDE = LIONSPARK_COORDINATES.latitude * DEG;
const SIN_LATITUDE = Math.sin(LATITUDE);
const COS_LATITUDE = Math.cos(LATITUDE);
const normalizeAngle = (angle: number) => ((angle % TAU) + TAU) % TAU;
const clampUnit = (value: number) => Math.max(-1, Math.min(1, value));
const sinDegrees = (angle: number) => Math.sin(angle * DEG);
const cosDegrees = (angle: number) => Math.cos(angle * DEG);

function julianCentury(epochMs: number) {
    return (epochMs / DAY_MS + 2_440_587.5 - 2_451_545) / 36_525;
}

function solarCoordinates(century: number) {
    const meanLongitude = (280.46646 + century * (36_000.76983 + century * 0.0003032)) % 360;
    const anomaly = 357.52911 + century * (35_999.05029 - 0.0001537 * century);
    const center =
        sinDegrees(anomaly) * (1.914602 - century * (0.004817 + 0.000014 * century)) +
        sinDegrees(2 * anomaly) * (0.019993 - 0.000101 * century) +
        sinDegrees(3 * anomaly) * 0.000289;
    const omega = 125.04 - 1934.136 * century;
    const longitude = (meanLongitude + center - 0.00569 - 0.00478 * sinDegrees(omega)) * DEG;
    const obliquity =
        (23 +
            (26 + (21.448 - century * (46.815 + century * (0.00059 - century * 0.001813))) / 60) /
                60 +
            0.00256 * cosDegrees(omega)) *
        DEG;
    return {
        rightAscension: Math.atan2(Math.cos(obliquity) * Math.sin(longitude), Math.cos(longitude)),
        declination: Math.asin(Math.sin(obliquity) * Math.sin(longitude)),
        obliquity,
    };
}

function lunarCoordinates(century: number, obliquity: number) {
    const t2 = century * century;
    const t3 = t2 * century;
    const t4 = t3 * century;
    const longitude =
        218.3164477 + 481_267.88123421 * century - 0.0015786 * t2 + t3 / 538841 - t4 / 65194000;
    const elongation =
        297.8501921 + 445_267.1114034 * century - 0.0018819 * t2 + t3 / 545868 - t4 / 113065000;
    const solarAnomaly = 357.5291092 + 35_999.0502909 * century - 0.0001536 * t2 + t3 / 24490000;
    const anomaly =
        134.9633964 + 477_198.8675055 * century + 0.0087414 * t2 + t3 / 69699 - t4 / 14712000;
    const argument =
        93.272095 + 483_202.0175233 * century - 0.0036539 * t2 - t3 / 3526000 + t4 / 863310000;
    const correctedLongitude =
        (longitude +
            6.289 * sinDegrees(anomaly) +
            1.274 * sinDegrees(2 * elongation - anomaly) +
            0.658 * sinDegrees(2 * elongation) +
            0.214 * sinDegrees(2 * anomaly) -
            0.186 * sinDegrees(solarAnomaly) -
            0.114 * sinDegrees(2 * argument)) *
        DEG;
    const latitude =
        (5.128 * sinDegrees(argument) +
            0.28 * sinDegrees(anomaly + argument) +
            0.277 * sinDegrees(anomaly - argument) +
            0.173 * sinDegrees(2 * elongation - argument) +
            0.055 * sinDegrees(2 * elongation + argument - anomaly) +
            0.046 * sinDegrees(2 * elongation - argument - anomaly) +
            0.033 * sinDegrees(2 * elongation + argument) +
            0.017 * sinDegrees(2 * anomaly + argument)) *
        DEG;
    const distanceKm =
        385_000.56 -
        20_905 * cosDegrees(anomaly) -
        3699 * cosDegrees(2 * elongation - anomaly) -
        2956 * cosDegrees(2 * elongation) -
        570 * cosDegrees(2 * anomaly);
    return {
        rightAscension: Math.atan2(
            Math.sin(correctedLongitude) * Math.cos(obliquity) -
                Math.tan(latitude) * Math.sin(obliquity),
            Math.cos(correctedLongitude),
        ),
        declination: Math.asin(
            Math.sin(latitude) * Math.cos(obliquity) +
                Math.cos(latitude) * Math.sin(obliquity) * Math.sin(correctedLongitude),
        ),
        distanceKm,
    };
}

function siderealAngle(century: number) {
    const days = century * 36_525;
    return normalizeAngle(
        (280.46061837 +
            360.98564736629 * days +
            0.000387933 * century * century -
            (century * century * century) / 38_710_000 +
            LIONSPARK_COORDINATES.longitude) *
            DEG,
    );
}

function horizonDirection(
    rightAscension: number,
    declination: number,
    sidereal: number,
): CelestialDirection {
    const hourAngle = sidereal - rightAscension;
    const cosDeclination = Math.cos(declination);
    const sinDeclination = Math.sin(declination);
    return {
        x: -cosDeclination * Math.sin(hourAngle),
        y: SIN_LATITUDE * sinDeclination + COS_LATITUDE * cosDeclination * Math.cos(hourAngle),
        z: SIN_LATITUDE * cosDeclination * Math.cos(hourAngle) - COS_LATITUDE * sinDeclination,
    };
}

/**
 * Equatorial axes in the world (+X east, +Y up, -Z geographic north).
 * For a world direction w, equatorial coordinates are
 * [dot(w, ra0), dot(w, ra90), dot(w, northPole)]. Then
 * RA = atan2(equatorial.y, equatorial.x), Dec = asin(equatorial.z).
 * A fixed RA/Dec sky texture therefore rotates with Earth continuously.
 */
export function equatorialToHorizonBasis(siderealRadians: number): EquatorialBasis {
    return {
        ra0: horizonDirection(0, 0, siderealRadians),
        ra90: horizonDirection(Math.PI / 2, 0, siderealRadians),
        northPole: { x: 0, y: SIN_LATITUDE, z: -COS_LATITUDE },
    };
}

export function sampleCelestial(epochMs: number): CelestialSample {
    if (!Number.isFinite(epochMs)) throw new RangeError('A finite epoch is required.');
    const century = julianCentury(epochMs);
    const solar = solarCoordinates(century);
    const lunar = lunarCoordinates(century, solar.obliquity);
    const siderealRadians = siderealAngle(century);
    const sunDirection = horizonDirection(solar.rightAscension, solar.declination, siderealRadians);
    const geocentricMoon = horizonDirection(
        lunar.rightAscension,
        lunar.declination,
        siderealRadians,
    );
    // Account for the observer's position on Earth; lunar horizon parallax is ~1°.
    const topocentricY = geocentricMoon.y - 6378.137 / lunar.distanceKm;
    const moonLength = Math.hypot(geocentricMoon.x, topocentricY, geocentricMoon.z);
    const moonDirection = {
        x: geocentricMoon.x / moonLength,
        y: topocentricY / moonLength,
        z: geocentricMoon.z / moonLength,
    };
    const elongation = Math.acos(
        clampUnit(
            sunDirection.x * geocentricMoon.x +
                sunDirection.y * geocentricMoon.y +
                sunDirection.z * geocentricMoon.z,
        ),
    );
    const sunDistanceKm = 149_597_870.7;
    const moonPhaseAngleRadians = Math.atan2(
        sunDistanceKm * Math.sin(elongation),
        lunar.distanceKm - sunDistanceKm * Math.cos(elongation),
    );
    return {
        sunDirection,
        sunAltitudeRadians: Math.asin(clampUnit(sunDirection.y)),
        sunAzimuthRadians: normalizeAngle(Math.atan2(sunDirection.x, -sunDirection.z)),
        moonDirection,
        moonAltitudeRadians: Math.asin(clampUnit(moonDirection.y)),
        moonIllumination: (1 + Math.cos(moonPhaseAngleRadians)) / 2,
        moonPhaseAngleRadians,
        siderealRadians,
        equatorialBasis: equatorialToHorizonBasis(siderealRadians),
    };
}

/**
 * Horizon previews on the supplied Korean calendar date. The center of the Sun
 * sits just above the dawn horizon (+0.4°), just below the dusk horizon (-0.4°).
 * These are deliberate visual moments, not published sunrise/sunset times.
 */
export function previewEpoch(epochMs: number, mode: 'sunrise' | 'sunset'): number {
    return previewEpochAtElevation(epochMs, mode, mode === 'sunrise' ? 0.4 : -0.4);
}

/**
 * The moment the Sun reaches a chosen geometric altitude on this Korean date.
 * Sunrise modes search the rising branch, sunset modes the falling branch, so a
 * preview can be staged at golden-hour elevations (5° at dawn, 8° at dusk)
 * rather than exactly on the horizon.
 */
export function previewEpochAtElevation(
    epochMs: number,
    mode: 'sunrise' | 'sunset',
    targetDegrees: number,
): number {
    if (!Number.isFinite(epochMs)) throw new RangeError('A finite epoch is required.');
    if (!Number.isFinite(targetDegrees) || Math.abs(targetDegrees) > 80)
        throw new RangeError('A preview altitude within ±80° is required.');
    const start = Math.floor((epochMs + KST_OFFSET_MS) / DAY_MS) * DAY_MS - KST_OFFSET_MS;
    const rising = mode === 'sunrise';
    const target = targetDegrees * DEG;
    const altitude = (epoch: number) => {
        const century = julianCentury(epoch);
        const solar = solarCoordinates(century);
        return (
            Math.asin(
                horizonDirection(solar.rightAscension, solar.declination, siderealAngle(century)).y,
            ) - target
        );
    };
    const step = 10 * 60_000;
    let previousEpoch = start;
    let previousAltitude = altitude(start);
    for (let nextEpoch = start + step; nextEpoch <= start + DAY_MS; nextEpoch += step) {
        const nextAltitude = altitude(nextEpoch);
        const crossing = rising
            ? previousAltitude <= 0 && nextAltitude >= 0
            : previousAltitude >= 0 && nextAltitude <= 0;
        if (crossing) {
            let low = previousEpoch;
            let high = nextEpoch;
            for (let iteration = 0; iteration < 25; iteration += 1) {
                const middle = (low + high) / 2;
                const value = altitude(middle);
                if (rising ? value < 0 : value > 0) low = middle;
                else high = middle;
            }
            return Math.round((low + high) / 2);
        }
        previousEpoch = nextEpoch;
        previousAltitude = nextAltitude;
    }
    // Daegu has both crossings in every season; an absent event is invalid input.
    throw new RangeError('No horizon crossing found for this Korean date.');
}
