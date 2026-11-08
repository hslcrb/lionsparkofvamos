import test from 'node:test';
import assert from 'node:assert/strict';
import { startQuietPlayback } from '../src/music';

function makeAudioGraph() {
    const calls: unknown[][] = [];
    let time = 10;
    const gain = {
        value: 1,
        cancelScheduledValues(at: number) {
            calls.push(['cancel', at]);
        },
        setValueAtTime(value: number, at: number) {
            this.value = value;
            calls.push(['set', value, at]);
        },
        linearRampToValueAtTime(value: number, at: number) {
            calls.push(['ramp', value, at]);
        },
    };
    const source = {
        connect(node: unknown) {
            calls.push(['source-connected', node]);
        },
    };
    const gainNode = {
        gain,
        connect(node: unknown) {
            calls.push(['gain-connected', node]);
        },
    };
    const context = {
        get currentTime() {
            return time;
        },
        destination: {},
        createMediaElementSource() {
            return source;
        },
        createGain() {
            return gainNode;
        },
        resume() {
            calls.push(['resume']);
            return Promise.resolve();
        },
    };
    return {
        calls,
        gain,
        context,
        setTime(value: number) {
            time = value;
        },
    };
}

test('starts silently and fades the audio signal to ten percent after playback begins', async () => {
    const graph = makeAudioGraph();
    let resolvePlay!: () => void;
    const audio = {
        volume: 1,
        play: () =>
            new Promise<void>((resolve) => {
                resolvePlay = resolve;
            }),
    };
    startQuietPlayback(audio as HTMLMediaElement, {
        createContext: () => graph.context as unknown as AudioContext,
    });
    assert.equal(graph.gain.value, 0);
    assert.ok(graph.calls.some((call) => call[0] === 'resume'));
    assert.ok(!graph.calls.some((call) => call[0] === 'ramp'));
    graph.setTime(15);
    resolvePlay();
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(
        graph.calls.find((call) => call[0] === 'ramp'),
        ['ramp', 0.1, 18],
    );
});

test('stopping during buffering prevents a later fade', async () => {
    const graph = makeAudioGraph();
    let resolvePlay!: () => void;
    const audio = {
        play: () =>
            new Promise<void>((resolve) => {
                resolvePlay = resolve;
            }),
    };
    const stop = startQuietPlayback(audio as HTMLMediaElement, {
        createContext: () => graph.context as unknown as AudioContext,
    });
    stop();
    resolvePlay();
    await new Promise((resolve) => setImmediate(resolve));
    assert.ok(!graph.calls.some((call) => call[0] === 'ramp'));
    assert.equal(graph.gain.value, 0);
});

test('without a safe audio graph the original audio never starts', () => {
    let played = false;
    let failed = false;
    const audio = {
        play() {
            played = true;
        },
    };
    startQuietPlayback(audio as HTMLMediaElement, {
        createContext: () => {
            throw new Error('unavailable');
        },
        onError: () => {
            failed = true;
        },
    });
    assert.equal(played, false);
    assert.equal(failed, true);
});

test('restarting music reuses its existing audio graph', async () => {
    const graph = makeAudioGraph();
    let contexts = 0;
    const audio = { play: () => Promise.resolve() };
    const options = {
        createContext: () => {
            contexts++;
            return graph.context as unknown as AudioContext;
        },
    };
    const stop = startQuietPlayback(audio as HTMLMediaElement, options);
    await new Promise((resolve) => setImmediate(resolve));
    stop();
    startQuietPlayback(audio as HTMLMediaElement, options);
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(contexts, 1);
    assert.equal(graph.calls.filter((call) => call[0] === 'source-connected').length, 1);
});

test('a rejected audio context silences and stops playback', async () => {
    const graph = makeAudioGraph();
    graph.context.resume = () => Promise.reject(new Error('blocked'));
    let paused = false;
    let failed = false;
    const audio = {
        play: () => Promise.resolve(),
        pause() {
            paused = true;
        },
    };
    startQuietPlayback(audio as HTMLMediaElement, {
        createContext: () => graph.context as unknown as AudioContext,
        onError: () => {
            failed = true;
        },
    });
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(failed, true);
    assert.equal(paused, true);
    assert.equal(graph.gain.value, 0);
    assert.ok(!graph.calls.some((call) => call[0] === 'ramp'));
});
