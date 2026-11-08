'use client';
import { useEffect, useRef, useState, type PointerEvent } from 'react';
import { makeScene } from './cinema/scene';
import type { Dance } from './room';
import Icon from './Icon';

interface Props {
    dance: Dance;
    entered: boolean;
    onEnter: () => void;
    onExit: () => void;
}

export default function Cinema({ dance, entered, onEnter, onExit }: Props) {
    const hostRef = useRef<HTMLDivElement | null>(null);
    const danceRef = useRef(dance);
    const viewRef = useRef({ entered, pan: 0 });
    const pointerRef = useRef<{ x: number; y: number; pan: number } | null>(null);
    const [unavailable, setUnavailable] = useState(false);
    useEffect(() => {
        danceRef.current = dance;
    }, [dance]);
    useEffect(() => {
        viewRef.current.entered = entered;
        if (!entered) viewRef.current.pan = 0;
    }, [entered]);
    useEffect(() => {
        if (hostRef.current) return makeScene(hostRef.current, danceRef, viewRef, setUnavailable);
    }, []);

    function startSwipe(event: PointerEvent<HTMLDivElement>) {
        if (event.target instanceof Element && event.target.closest('button')) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        pointerRef.current = { x: event.clientX, y: event.clientY, pan: viewRef.current.pan };
    }

    function moveSwipe(event: PointerEvent<HTMLDivElement>) {
        const start = pointerRef.current;
        if (!start || !entered) return;
        const deltaX = event.clientX - start.x;
        if (Math.abs(deltaX) > Math.abs(event.clientY - start.y)) {
            viewRef.current.pan = Math.max(-1, Math.min(1, start.pan - deltaX / 180));
        }
    }

    function endSwipe(event: PointerEvent<HTMLDivElement>) {
        const start = pointerRef.current;
        pointerRef.current = null;
        if (!start || entered) return;
        const deltaX = event.clientX - start.x;
        const deltaY = event.clientY - start.y;
        if (deltaX < -45 && Math.abs(deltaX) > Math.abs(deltaY) * 1.2) onEnter();
    }

    return (
        <div
            className={`cinema-shell ${entered ? 'is-entered' : ''}`}
            onPointerDown={startSwipe}
            onPointerMove={moveSwipe}
            onPointerUp={endSwipe}
            onPointerCancel={() => {
                pointerRef.current = null;
            }}
        >
            <div
                className="cinema-canvas"
                ref={hostRef}
                role="img"
                aria-label={
                    entered
                        ? '삼성 라이온즈 응원관에 입장했습니다. 좌우로 밀어 영화관을 둘러보세요.'
                        : '삼성 라이온즈 응원관의 아기 사자들'
                }
            />
            {!unavailable && !entered && (
                <div className="cinema-entry">
                    <span className="cinema-entry-hint">
                        왼쪽으로 밀어서 입장{' '}
                        <b>
                            <Icon name="arrow-left" />
                        </b>
                    </span>
                    <button className="cinema-entry-button" type="button" onClick={onEnter}>
                        응원관 들어가기{' '}
                        <span>
                            <Icon name="arrow-up-right" />
                        </span>
                    </button>
                </div>
            )}
            {!unavailable && entered && (
                <div className="cinema-inside">
                    <span>
                        <Icon name="sparkle" /> 응원관 입장 · 좌우로 밀어 둘러보기
                    </span>
                    <button type="button" onClick={onExit}>
                        나가기
                    </button>
                </div>
            )}
            {unavailable && (
                <p className="cinema-fallback">
                    응원관을 불러오지 못했습니다. 다른 브라우저에서 다시 시도해 주세요.
                </p>
            )}
        </div>
    );
}
