'use client';

import { assetPath } from '../asset-path';
import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useRef,
    useState,
    type ReactNode,
} from 'react';
import { usePathname } from 'next/navigation';
import { disposePlayback, startQuietPlayback } from '../music';

type MusicStatus = 'off' | 'loading' | 'playing' | 'error';
interface MusicContextValue {
    status: MusicStatus;
    play: () => void;
    stop: () => void;
}
const MusicContext = createContext<MusicContextValue | null>(null);

export function MusicProvider({ children }: { children: ReactNode }) {
    const pathname = usePathname();
    const [status, setStatus] = useState<MusicStatus>('off');
    const audio = useRef<HTMLAudioElement | null>(null);
    const stopFade = useRef<() => void>(() => {});

    const stop = useCallback(() => {
        stopFade.current();
        audio.current?.pause();
        setStatus('off');
    }, []);

    const play = useCallback(() => {
        if (!audio.current) {
            audio.current = new Audio(assetPath('/my-lions.mp3'));
            audio.current.loop = true;
            audio.current.addEventListener('pause', () => setStatus('off'));
        }
        stopFade.current();
        setStatus('loading');
        stopFade.current = startQuietPlayback(audio.current, {
            onStarted: () => setStatus('playing'),
            onError: () => setStatus('error'),
        });
    }, []);

    useEffect(() => {
        if (pathname !== '/main') {
            stopFade.current();
            audio.current?.pause();
        }
    }, [pathname]);

    useEffect(
        () => () => {
            stopFade.current();
            if (audio.current) disposePlayback(audio.current);
        },
        [],
    );

    return <MusicContext.Provider value={{ status, play, stop }}>{children}</MusicContext.Provider>;
}

export function useMusic(): MusicContextValue {
    const music = useContext(MusicContext);
    if (!music) throw new Error('MusicProvider is missing');
    return music;
}

export function MusicControl() {
    const { status, play, stop } = useMusic();
    const active = status === 'playing' || status === 'loading';
    return (
        <aside className="music-control" aria-label="배경 음악">
            {status === 'error' && (
                <p className="music-error" role="status">
                    재생할 수 없어요. 다시 시도해 주세요.
                </p>
            )}
            <div className="music-player">
                <span className="music-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none">
                        <path
                            d="M9 18V6l10-2v12M9 18c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2Zm10-2c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2Z"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />
                    </svg>
                </span>
                <span className="music-info">
                    <strong>나의 라이온즈</strong>
                    <span role="status">
                        {status === 'loading'
                            ? '재생 준비 중'
                            : status === 'playing'
                              ? '재생 중'
                              : '음악 꺼짐'}
                    </span>
                </span>
                <button
                    type="button"
                    onClick={active ? stop : play}
                    aria-label={active ? '나의 라이온즈 음악 끄기' : '나의 라이온즈 음악 켜기'}
                >
                    {active ? '끄기' : '켜기'}
                </button>
            </div>
        </aside>
    );
}
