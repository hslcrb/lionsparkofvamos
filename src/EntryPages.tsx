import React, { type ReactNode } from 'react';
import Link from 'next/link';
import EnterMainLink from './components/enter-main-link';
import LionsLogos from './LionsLogos';

function EntryShell({ children }: { children: ReactNode }) {
    return (
        <div className="entry-shell">
            <header className="entry-header">
                <Link className="entry-brand" href="/" aria-label="더 라이온즈 버튼 처음으로">
                    <span className="entry-brand-mark" aria-hidden="true">
                        ✳
                    </span>
                    <span>
                        THE LIONS
                        <br />
                        <strong>BUTTON</strong>
                    </span>
                </Link>
                <span className="entry-header-note">FOR EVERY BLUE HEART</span>
            </header>
            {children}
            <footer className="entry-footer">
                <span>삼성을 사랑하는 팬들이 만드는 응원 공간</span>
                <span>비공식 팬 프로젝트 · GO LIONS!</span>
            </footer>
        </div>
    );
}

function Arrow() {
    return (
        <span className="entry-arrow" aria-hidden="true">
            ↗
        </span>
    );
}

export function EntryPage() {
    return (
        <main className="entry-shell gateway" id="entry-main">
            <div className="gateway-content">
                <LionsLogos className="gateway-logos" />
                <nav className="gateway-destinations" aria-label="입장할 곳 선택">
                    <EnterMainLink />
                    <Link className="gateway-button gateway-button-secondary" href="/lionspark">
                        라팍월드 들어가기
                    </Link>
                </nav>
            </div>
        </main>
    );
}

function MessagePage({
    eyebrow,
    title,
    children,
}: {
    eyebrow: string;
    title: ReactNode;
    children: ReactNode;
}) {
    return (
        <EntryShell>
            <main className="entry-main entry-message-main">
                <div className="entry-message">
                    <p className="entry-kicker">
                        <span aria-hidden="true"></span> {eyebrow}
                    </p>
                    <h1>{title}</h1>
                    <div className="entry-description">{children}</div>
                    <Link className="entry-back" href="/">
                        처음으로 돌아가기 <Arrow />
                    </Link>
                </div>
            </main>
        </EntryShell>
    );
}

export function ComingSoonPage() {
    return (
        <MessagePage
            eyebrow="LIONSPARK WORLD"
            title={
                <>
                    라팍월드,
                    <br />
                    <em>준비하고 있어요.</em>
                </>
            }
        >
            새로운 공간에서 만날 날을 기다려 주세요.
        </MessagePage>
    );
}

export function NotFoundPage() {
    return (
        <MessagePage
            eyebrow="404 · PAGE NOT FOUND"
            title={
                <>
                    이 페이지는
                    <br />
                    <em>찾을 수 없어요.</em>
                </>
            }
        >
            주소를 다시 확인하거나 처음으로 돌아가 주세요.
        </MessagePage>
    );
}

export function TeapotPage() {
    return (
        <MessagePage
            eyebrow="418 · I'M A TEAPOT"
            title={
                <>
                    앗, 저는
                    <br />
                    <em>주전자예요.</em>
                </>
            }
        >
            커피는 못 끓여도 라이온즈는 응원할 수 있어요.
        </MessagePage>
    );
}

export function UnavailablePage({ retry }: { retry: () => void }) {
    return (
        <MessagePage eyebrow="SOMETHING WENT WRONG" title="잠시 문제가 생겼어요.">
            <span>다시 시도해 주세요.</span>
            <br />
            <button className="entry-back" type="button" onClick={retry}>
                다시 시도
            </button>
        </MessagePage>
    );
}
