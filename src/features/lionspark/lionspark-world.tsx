'use client';

import Link from 'next/link';
import {
    useEffect,
    useRef,
    useState,
    type CSSProperties,
    type KeyboardEvent,
    type PointerEvent,
} from 'react';
import {
    createParkRuntime,
    type ParkRuntime,
    type ParkSnapshot,
    type ParkTimeMode,
    type ParkView,
} from './runtime';
import styles from './lionspark.module.css';

type LoadStatus = 'loading' | 'ready' | 'error';

const INITIAL_SNAPSHOT: ParkSnapshot = {
    view: 'walk',
    timeLabel: '--:--:--',
    timeMode: 'live',
    running: false,
    speedKmh: 0,
};
const MOVEMENT_KEYS = new Set([
    'arrowup',
    'arrowdown',
    'arrowleft',
    'arrowright',
    'w',
    's',
    'a',
    'd',
]);

export default function LionsparkWorld() {
    // 런타임 연결과 상태 동기화 / Runtime lifecycle and state synchronization
    const viewport = useRef<HTMLDivElement>(null);
    const runtime = useRef<ParkRuntime | null>(null);
    const joystick = useRef<number | null>(null);
    const keyboardKeys = useRef(new Set<string>());
    const lastView = useRef<ParkView>('walk');
    const [status, setStatus] = useState<LoadStatus>('loading');
    const [progress, setProgress] = useState(0);
    const [attempt, setAttempt] = useState(0);
    const [snapshot, setSnapshot] = useState<ParkSnapshot>(INITIAL_SNAPSHOT);
    const [started, setStarted] = useState(false);
    const [thumb, setThumb] = useState({ x: 0, y: 0 });
    const [braking, setBraking] = useState(false);
    const { view, timeLabel, timeMode, running, speedKmh, notice } = snapshot;

    useEffect(() => {
        const element = viewport.current;
        if (!element) return;
        let active = true;
        let mounted: ParkRuntime | null = null;
        async function initialize() {
            mounted = createParkRuntime(
                element!,
                (value) => {
                    if (active) setProgress(value);
                },
                (next) => {
                    if (!active) return;
                    if (lastView.current !== next.view) {
                        lastView.current = next.view;
                        joystick.current = null;
                        keyboardKeys.current.clear();
                        setThumb({ x: 0, y: 0 });
                        setBraking(false);
                        setStarted(true);
                    }
                    const updated = { ...next, speedKmh: Math.round(next.speedKmh) };
                    setSnapshot((current) =>
                        current.view === updated.view &&
                        current.timeLabel === updated.timeLabel &&
                        current.timeMode === updated.timeMode &&
                        current.running === updated.running &&
                        current.speedKmh === updated.speedKmh &&
                        current.notice === updated.notice
                            ? current
                            : updated,
                    );
                },
            );
            runtime.current = mounted;
            await mounted.ready;
            if (active) setStatus('ready');
        }
        void initialize().catch(() => {
            if (active) setStatus('error');
        });
        return () => {
            active = false;
            mounted?.dispose();
            runtime.current = null;
        };
    }, [attempt]);

    useEffect(() => {
        function clearInput() {
            joystick.current = null;
            keyboardKeys.current.clear();
            setThumb({ x: 0, y: 0 });
            setBraking(false);
            runtime.current?.setTouchMovement(0, 0);
            runtime.current?.setRunning(false);
            runtime.current?.setBraking(false);
        }
        function visibilityChanged() {
            if (document.hidden) clearInput();
        }
        window.addEventListener('blur', clearInput);
        document.addEventListener('visibilitychange', visibilityChanged);
        return () => {
            window.removeEventListener('blur', clearInput);
            document.removeEventListener('visibilitychange', visibilityChanged);
        };
    }, []);

    // 시점·시간 선택과 출발점 복귀 / View, time and spawn controls
    function clearMovement() {
        joystick.current = null;
        keyboardKeys.current.clear();
        setThumb({ x: 0, y: 0 });
        setBraking(false);
        runtime.current?.setTouchMovement(0, 0);
        runtime.current?.setRunning(false);
        runtime.current?.setBraking(false);
    }
    function chooseView(next: ParkView) {
        clearMovement();
        runtime.current?.setView(next);
        runtime.current?.focus();
        setStarted(true);
    }
    function chooseTime(next: ParkTimeMode) {
        runtime.current?.setTimeMode(next);
        runtime.current?.focus();
    }
    function toggleRunning() {
        runtime.current?.setRunning(!running);
        runtime.current?.focus();
    }
    function reset() {
        clearMovement();
        runtime.current?.reset();
        runtime.current?.focus();
        setStarted(true);
    }
    function retry() {
        clearMovement();
        setStatus('loading');
        setProgress(0);
        setSnapshot(INITIAL_SNAPSHOT);
        lastView.current = 'walk';
        setStarted(false);
        setAttempt((current) => current + 1);
    }

    // 터치와 키보드 이동 패드 / Touch and keyboard movement pad
    function moveJoystick(event: PointerEvent<HTMLButtonElement>) {
        if (joystick.current !== event.pointerId) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        const radius = bounds.width * 0.32;
        const x = (event.clientX - bounds.left - bounds.width / 2) / radius;
        const y = (event.clientY - bounds.top - bounds.height / 2) / radius;
        const length = Math.max(1, Math.hypot(x, y));
        const next = { x: x / length, y: y / length };
        setThumb(next);
        runtime.current?.setTouchMovement(-next.y, next.x);
    }
    function beginJoystick(event: PointerEvent<HTMLButtonElement>) {
        event.preventDefault();
        event.currentTarget.setPointerCapture(event.pointerId);
        joystick.current = event.pointerId;
        setStarted(true);
        moveJoystick(event);
    }
    function endJoystick() {
        joystick.current = null;
        if (keyboardKeys.current.has('shift')) runtime.current?.setRunning(false);
        keyboardKeys.current.clear();
        setThumb({ x: 0, y: 0 });
        runtime.current?.setTouchMovement(0, 0);
    }
    function updateKeyboardMovement() {
        const keys = keyboardKeys.current;
        const x =
            Number(keys.has('arrowright') || keys.has('d')) -
            Number(keys.has('arrowleft') || keys.has('a'));
        const y =
            Number(keys.has('arrowdown') || keys.has('s')) -
            Number(keys.has('arrowup') || keys.has('w'));
        const length = Math.max(1, Math.hypot(x, y));
        const next = { x: x / length, y: y / length };
        setThumb(next);
        runtime.current?.setTouchMovement(-next.y, next.x);
    }
    function joystickKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
        const key = event.key.toLowerCase();
        if (key === 'shift' && view === 'walk') {
            keyboardKeys.current.add(key);
            runtime.current?.setRunning(true);
        }
        if (!MOVEMENT_KEYS.has(key)) return;
        event.preventDefault();
        keyboardKeys.current.add(key);
        setStarted(true);
        updateKeyboardMovement();
    }
    function joystickKeyUp(event: KeyboardEvent<HTMLButtonElement>) {
        const key = event.key.toLowerCase();
        if (key === 'shift') runtime.current?.setRunning(false);
        if (!MOVEMENT_KEYS.has(key) && key !== 'shift') return;
        event.preventDefault();
        keyboardKeys.current.delete(key);
        updateKeyboardMovement();
    }

    // 누르는 동안 차량 제동 / Hold-to-brake vehicle control
    function setBrake(next: boolean) {
        setBraking(next);
        runtime.current?.setBraking(next);
    }
    function brakeKey(event: KeyboardEvent<HTMLButtonElement>, pressed: boolean) {
        if (event.key !== ' ' && event.key !== 'Enter') return;
        event.preventDefault();
        setBrake(pressed);
    }

    return (
        <main className={styles.world} aria-label="라팍월드">
            <div
                className={styles.viewport}
                ref={viewport}
                tabIndex={0}
                role="region"
                aria-label="라팍 3D 화면"
                aria-describedby={status === 'ready' ? 'park-controls-hint' : undefined}
                onPointerDown={() => {
                    if (status === 'ready') setStarted(true);
                }}
                onKeyDown={(event) => {
                    if (
                        status === 'ready' &&
                        (MOVEMENT_KEYS.has(event.key.toLowerCase()) ||
                            ['Shift', 'e', 'E', ' '].includes(event.key))
                    ) {
                        setStarted(true);
                    }
                }}
            />
            {/* 상단 안내와 장면 설정 / Header and scene settings */}
            <div className={styles.hud}>
                <header className={styles.header}>
                    <div className={styles.identity}>
                        <span className={styles.kicker}>LIONSPARK WORLD</span>
                        <h1>대구 삼성 라이온즈파크</h1>
                    </div>
                    <Link className={styles.back} href="/main">
                        메인으로 <span aria-hidden="true">↗</span>
                    </Link>
                </header>
                {status === 'ready' && (
                    <section className={styles['control-dock']} aria-label="라팍 탐색 설정">
                        <div className={styles['clock-row']}>
                            <div className={styles.clock}>
                                <span>{timeMode === 'live' ? '한국 시간' : '장면 시간'}</span>
                                <strong>{timeLabel}</strong>
                            </div>
                            <span className={styles['clock-caption']}>
                                {timeMode === 'live'
                                    ? 'KST · UTC+9'
                                    : timeMode === 'sunrise'
                                      ? '해돋이 5° 미리보기'
                                      : timeMode === 'sunset'
                                        ? '노을 8° 미리보기'
                                        : timeMode === 'day'
                                          ? '한낮 미리보기'
                                          : '조명 켜진 밤'}
                            </span>
                        </div>
                        <div className={styles['time-options']} role="group" aria-label="장면 시간">
                            <button
                                type="button"
                                aria-pressed={timeMode === 'live'}
                                onClick={() => chooseTime('live')}
                            >
                                <span aria-hidden="true">🕒</span> 실시간
                            </button>
                            <button
                                type="button"
                                aria-pressed={timeMode === 'sunrise'}
                                onClick={() => chooseTime('sunrise')}
                            >
                                <span aria-hidden="true">🌅</span> 일출
                            </button>
                            <button
                                type="button"
                                aria-pressed={timeMode === 'day'}
                                onClick={() => chooseTime('day')}
                            >
                                <span aria-hidden="true">☀️</span> 낮
                            </button>
                            <button
                                type="button"
                                aria-pressed={timeMode === 'sunset'}
                                onClick={() => chooseTime('sunset')}
                            >
                                <span aria-hidden="true">🌇</span> 노을
                            </button>
                            <button
                                type="button"
                                aria-pressed={timeMode === 'night'}
                                onClick={() => chooseTime('night')}
                            >
                                <span aria-hidden="true">🌙</span> 밤
                            </button>
                        </div>
                        <nav className={styles.views} aria-label="라팍 시점">
                            <button
                                type="button"
                                aria-pressed={view === 'walk'}
                                onClick={() => chooseView('walk')}
                            >
                                보행
                            </button>
                            <button
                                type="button"
                                aria-pressed={view === 'drive'}
                                onClick={() => chooseView(view === 'drive' ? 'walk' : 'drive')}
                            >
                                {view === 'drive' ? '차량 하차' : '차량 탑승'}
                            </button>
                            <button
                                type="button"
                                aria-pressed={view === 'overview'}
                                onClick={() => chooseView('overview')}
                            >
                                전체 전경
                            </button>
                            <button
                                className={styles.reset}
                                type="button"
                                onClick={reset}
                                aria-label="광장 출발점으로 돌아가기"
                            >
                                <span aria-hidden="true">↺</span>
                            </button>
                        </nav>
                    </section>
                )}
            </div>
            {/* 로딩·오류 안내 / Loading and recovery */}
            {status !== 'ready' && (
                <div className={styles.screen}>
                    <section className={styles.loadCard} aria-labelledby="park-load-title">
                        <span className={styles.kicker}>OUR BLUE, OUR BALLPARK</span>
                        <h2 id="park-load-title">
                            {status === 'error'
                                ? '라팍을 불러오지 못했어요.'
                                : '라팍으로 가는 중이에요.'}
                        </h2>
                        {status === 'error' ? (
                            <>
                                <p>
                                    연결 상태를 확인하고 다시 불러와 주세요.
                                    <br />
                                    WebGL을 지원하는 브라우저에서 이용할 수 있어요.
                                </p>
                                <button className={styles.primary} type="button" onClick={retry}>
                                    다시 불러오기
                                </button>
                            </>
                        ) : (
                            <>
                                <p>푸른 관중석과 경기장 주변을 준비하고 있어요.</p>
                                <div
                                    className={styles.progress}
                                    role="progressbar"
                                    aria-label="라팍 불러오기"
                                    aria-valuemin={0}
                                    aria-valuemax={100}
                                    aria-valuenow={Math.round(progress * 100)}
                                >
                                    <span style={{ width: `${progress * 100}%` }} />
                                </div>
                                <span className={styles.percent}>
                                    {Math.round(progress * 100)}%
                                </span>
                            </>
                        )}
                    </section>
                </div>
            )}
            {/* 탐색 안내와 이동 제어 / Exploration guidance and movement controls */}
            {status === 'ready' && (
                <>
                    {!started && (
                        <section className={styles.welcome} aria-labelledby="park-welcome-title">
                            <span className={styles.kicker}>파란 마음으로, 라팍 산책</span>
                            <h2 id="park-welcome-title">우리의 야구장을 걸어볼까요?</h2>
                            <p>광장을 산책하거나 차에 올라 라팍을 둘러보세요.</p>
                            <button
                                className={styles.primary}
                                type="button"
                                onClick={() => {
                                    reset();
                                    runtime.current?.focus();
                                }}
                            >
                                걸어보기 <span aria-hidden="true">→</span>
                            </button>
                        </section>
                    )}
                    {notice && (
                        <p className={styles.notice} role="status">
                            {notice}
                        </p>
                    )}
                    <div className={styles.instructions} id="park-controls-hint">
                        {view === 'walk' ? (
                            <>
                                <span className={styles.desktopHint}>
                                    <kbd>W A S D</kbd> 이동 · <kbd>Shift</kbd> 달리기 · <kbd>E</kbd>{' '}
                                    차량 탑승 · 드래그로 시선 이동
                                </span>
                                <span className={styles.mobileHint}>
                                    패드로 이동 · 달리기 버튼 · 화면을 밀어 둘러보기
                                </span>
                            </>
                        ) : view === 'drive' ? (
                            <>
                                <span className={styles.desktopHint}>
                                    <kbd>W S</kbd> 가속·후진 · <kbd>A D</kbd> 조향 ·{' '}
                                    <kbd>Space</kbd> 제동 · <kbd>E</kbd> 하차
                                </span>
                                <span className={styles.mobileHint}>
                                    패드 위아래로 가속·후진 · 좌우로 조향 · 눌러 제동
                                </span>
                            </>
                        ) : (
                            <span>드래그로 회전 · 휠 또는 두 손가락으로 확대</span>
                        )}
                    </div>
                    {view !== 'overview' && (
                        <div className={styles['movement-controls']}>
                            <button
                                className={styles.joystick}
                                type="button"
                                aria-label={
                                    view === 'drive'
                                        ? '차량 조작 패드. 위아래로 가속과 후진, 좌우로 조향합니다. 방향키로도 조작할 수 있어요.'
                                        : '이동 패드. 누른 채 원하는 방향으로 움직이세요. 방향키로도 이동할 수 있어요.'
                                }
                                onPointerDown={beginJoystick}
                                onPointerMove={moveJoystick}
                                onPointerUp={endJoystick}
                                onPointerCancel={endJoystick}
                                onLostPointerCapture={endJoystick}
                                onKeyDown={joystickKeyDown}
                                onKeyUp={joystickKeyUp}
                                onBlur={endJoystick}
                                style={
                                    {
                                        '--thumb-x': `${thumb.x * 31}px`,
                                        '--thumb-y': `${thumb.y * 31}px`,
                                    } as CSSProperties
                                }
                            >
                                <span className={styles.joystickDirections} aria-hidden="true">
                                    ＋
                                </span>
                                <span className={styles.thumb} aria-hidden="true" />
                            </button>
                            <div className={styles['movement-actions']}>
                                {view === 'drive' ? (
                                    <>
                                        <output
                                            className={styles.speed}
                                            aria-label={`차량 속도 시속 ${speedKmh}킬로미터`}
                                            aria-live="off"
                                        >
                                            <strong>{speedKmh}</strong>
                                            <span>km/h</span>
                                        </output>
                                        <button
                                            className={styles['action-button']}
                                            type="button"
                                            aria-label="브레이크. 누르는 동안 제동합니다."
                                            aria-pressed={braking}
                                            onPointerDown={(event) => {
                                                event.preventDefault();
                                                event.currentTarget.setPointerCapture(
                                                    event.pointerId,
                                                );
                                                setBrake(true);
                                            }}
                                            onPointerUp={(event) => {
                                                setBrake(false);
                                                if (event.pointerType === 'mouse') {
                                                    runtime.current?.focus();
                                                }
                                            }}
                                            onPointerCancel={() => setBrake(false)}
                                            onLostPointerCapture={() => setBrake(false)}
                                            onKeyDown={(event) => brakeKey(event, true)}
                                            onKeyUp={(event) => brakeKey(event, false)}
                                            onClick={(event) => {
                                                if (event.detail === 0) setBrake(!braking);
                                            }}
                                            onBlur={() => setBrake(false)}
                                        >
                                            브레이크
                                        </button>
                                    </>
                                ) : (
                                    <button
                                        className={styles['action-button']}
                                        type="button"
                                        aria-pressed={running}
                                        onClick={toggleRunning}
                                    >
                                        {running ? '달리는 중' : '달리기'}
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                    <span className={styles.credit}>
                        비공식 팬 공간 · 사진을 바탕으로 재구성한 3D 라팍
                    </span>
                </>
            )}
        </main>
    );
}
