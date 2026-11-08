const TARGET_VOLUME = 0.1;
const FADE_DURATION = 3;
interface AudioGraph {
    context: AudioContext;
    gain: GainNode;
}
interface PlaybackOptions {
    createContext?: () => AudioContext;
    onError?: (error: unknown) => void;
    onStarted?: () => void;
}
const audioGraphs = new WeakMap<HTMLMediaElement, AudioGraph>();

function createAudioGraph(audio: HTMLMediaElement, createContext?: () => AudioContext): AudioGraph {
    const AudioContextClass =
        globalThis.AudioContext ||
        (globalThis as typeof globalThis & { webkitAudioContext?: typeof AudioContext })
            .webkitAudioContext;
    if (!createContext && !AudioContextClass) throw new Error('Web Audio is unavailable');
    const context = createContext ? createContext() : new AudioContextClass!();
    const gain = context.createGain();
    gain.gain.value = 0;
    gain.connect(context.destination);
    const source = context.createMediaElementSource(audio);
    source.connect(gain);
    return { context, gain };
}

export function startQuietPlayback(audio: HTMLMediaElement, options: PlaybackOptions = {}) {
    let active = true;
    let graph: AudioGraph | undefined;

    function silence() {
        if (!graph) return;
        const { context, gain } = graph;
        gain.gain.cancelScheduledValues(context.currentTime);
        gain.gain.setValueAtTime(0, context.currentTime);
    }

    function fail(error: unknown) {
        if (!active) return;
        active = false;
        silence();
        audio.pause?.();
        options.onError?.(error);
    }

    try {
        graph = audioGraphs.get(audio);
        if (!graph) {
            graph = createAudioGraph(audio, options.createContext);
            audioGraphs.set(audio, graph);
        }
        silence();
        audio.volume = 1;
        const playbackGraph = graph;
        const resume = playbackGraph.context.resume();
        const playback = audio.play();
        Promise.all([resume, playback])
            .then(() => {
                if (!active) return;
                const { context, gain } = playbackGraph;
                gain.gain.setValueAtTime(0, context.currentTime);
                gain.gain.linearRampToValueAtTime(
                    TARGET_VOLUME,
                    context.currentTime + FADE_DURATION,
                );
                options.onStarted?.();
            })
            .catch(fail);
    } catch (error) {
        fail(error);
    }

    return () => {
        active = false;
        silence();
    };
}

export function disposePlayback(audio: HTMLMediaElement): void {
    audio.pause();
    const graph = audioGraphs.get(audio);
    if (graph) {
        graph.gain.disconnect();
        void graph.context.close().catch(() => {});
        audioGraphs.delete(audio);
    }
    audio.removeAttribute('src');
    audio.load();
}
