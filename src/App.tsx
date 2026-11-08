'use client';
import { useRef, useState, type TouchEvent } from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import { useCheerRoom } from './hooks/use-cheer-room';
import { useCheerBursts } from './hooks/use-cheer-bursts';
import CheerCard from './components/cheer-card';
import DancePanel from './components/dance-panel';
const Cinema = dynamic(() => import('./Cinema'), {
    ssr: false,
    loading: () => <div className="cinema-loading">응원관 불러오는 중</div>,
});
import { isCinemaSwipe, type Point } from './gesture';
import Icon from './Icon';
import LionsLogos from './LionsLogos';

function App() {
    const { room, connected, dance, activeMove, chooseMove, send } = useCheerRoom();
    const { bursts, cheer } = useCheerBursts(send);
    const [entered, setEntered] = useState(false);
    const [moving, setMoving] = useState(true);
    const touchStart = useRef<Point | null>(null);

    function enterCinema() {
        setEntered(true);
        window.location.hash = 'cinema';
        document.getElementById('cinema')?.scrollIntoView({
            behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
                ? 'auto'
                : 'smooth',
        });
    }

    function startSwipe(event: TouchEvent<HTMLElement>) {
        const touch = event.touches[0];
        if (event.touches.length !== 1 || !touch) return;
        touchStart.current = { x: touch.clientX, y: touch.clientY };
    }

    function finishSwipe(event: TouchEvent<HTMLElement>) {
        const touch = event.changedTouches[0];
        if (touch && isCinemaSwipe(touchStart.current, { x: touch.clientX, y: touch.clientY }))
            enterCinema();
        touchStart.current = null;
    }

    return (
        <div className="site-wrap" data-motion={moving ? 'playing' : 'paused'}>
            <header className="site-header">
                <a className="brand" href="#top" aria-label="라이온즈 응원관 처음으로">
                    <Image className="brand-logo" src="/lions.svg" alt="" width={65} height={48} />
                    <span>
                        THE LIONS
                        <br />
                        <strong>BUTTON</strong>
                    </span>
                </a>
                <div className="header-right">
                    <button
                        className="motion-toggle"
                        type="button"
                        onClick={() => setMoving((value) => !value)}
                        aria-pressed={!moving}
                    >
                        <span aria-hidden="true">{moving ? 'Ⅱ' : '▷'}</span>
                        {moving ? '움직임 멈춤' : '움직임 켜기'}
                    </button>
                    <a href="#cinema" className="header-link" onClick={enterCinema}>
                        응원관 입장{' '}
                        <span>
                            <Icon name="arrow-up-right" />
                        </span>
                    </a>
                </div>
            </header>

            <main id="top">
                <section
                    className="hero"
                    aria-labelledby="hero-title"
                    onTouchStart={startSwipe}
                    onTouchEnd={finishSwipe}
                >
                    <div className="hero-light" aria-hidden="true" />
                    <div className="hero-flutes" aria-hidden="true" />
                    <div className="hero-logos" aria-label="삼성 라이온즈와 2026 VAMOS 로고">
                        <Image src="/lions.svg" alt="삼성 라이온즈" width={245} height={180} />
                        <Image
                            src="/vamos.svg"
                            alt="2026 한국시리즈 VAMOS"
                            width={245}
                            height={180}
                        />
                    </div>
                    <div className="hero-copy">
                        <h1 id="hero-title">
                            가자 삼성!
                            <br />
                            <span>가자 라이온즈!</span>
                        </h1>
                        <button type="button" className="swipe-entry" onClick={enterCinema}>
                            응원관 보기{' '}
                            <span>
                                <Icon name="arrow-up-right" />
                            </span>
                        </button>
                    </div>
                    <CheerCard
                        room={room}
                        connected={connected}
                        bursts={bursts}
                        onCheer={cheer}
                        moving={moving}
                    />
                </section>

                <div className="ticker" aria-hidden="true">
                    <div>
                        승리하리라{' '}
                        <span>
                            <Icon name="asterisk" />
                        </span>{' '}
                        최강삼성 이겨라{' '}
                        <span>
                            <Icon name="asterisk" />
                        </span>{' '}
                        VAMOS LIONS!{' '}
                        <span>
                            <Icon name="asterisk" />
                        </span>{' '}
                        승리하리라{' '}
                        <span>
                            <Icon name="asterisk" />
                        </span>{' '}
                        최강삼성 이겨라{' '}
                        <span>
                            <Icon name="asterisk" />
                        </span>
                    </div>
                </div>

                <section className="cinema-section" id="cinema" aria-labelledby="cinema-title">
                    <div className="section-heading">
                        <div>
                            <h2 id="cinema-title">응원관</h2>
                        </div>
                        <p>동작을 고르고 응원관을 둘러보세요.</p>
                    </div>
                    <div className="cinema-layout">
                        <div className="cinema-frame">
                            <div className="cinema-toolbar">
                                <span>
                                    <i></i> LIONS CINEMA
                                </span>
                                <span>
                                    {connected && room.online !== null
                                        ? `${room.online.toLocaleString('ko-KR')}명 접속 중`
                                        : '응원관 연결 중'}
                                </span>
                            </div>
                            <Cinema
                                dance={dance}
                                entered={entered}
                                onEnter={enterCinema}
                                onExit={() => setEntered(false)}
                            />
                            <div className="cinema-caption">
                                <span>LIONS CINEMA</span>
                                <span>삼성 라이온즈 응원관</span>
                            </div>
                        </div>
                        <DancePanel
                            connected={connected}
                            activeMove={activeMove}
                            onChoose={chooseMove}
                        />
                    </div>
                </section>
                <section className="closing" aria-labelledby="closing-title">
                    <div className="closing-stars">
                        <Icon name="sparkle" /> &nbsp; <Icon name="asterisk" /> &nbsp;{' '}
                        <Icon name="sparkle" />
                    </div>
                    <h2 id="closing-title">우리는 라이온즈다</h2>
                    <LionsLogos className="closing-logos" />
                    <a href="#top" className="back-top">
                        맨 위로 <Icon name="arrow-up" />
                    </a>
                </section>
            </main>
        </div>
    );
}

export default App;
