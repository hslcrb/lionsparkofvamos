'use client';
import Link from 'next/link';
import { useMusic } from './music-provider';

export default function EnterMainLink() {
    const { play } = useMusic();
    return (
        <Link
            className="gateway-button gateway-button-primary"
            href="/main"
            onClick={(event) => {
                if (
                    event.button === 0 &&
                    !event.metaKey &&
                    !event.ctrlKey &&
                    !event.shiftKey &&
                    !event.altKey
                )
                    play();
            }}
        >
            메인으로 바로 접속
        </Link>
    );
}
