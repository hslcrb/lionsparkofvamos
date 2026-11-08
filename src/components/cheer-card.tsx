import type { CSSProperties } from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import Icon from '../Icon';
import type { RoomState } from '../room';

const GlassEmblem = dynamic(() => import('./glass-emblem'), { ssr: false });
interface Props {
    room: RoomState;
    connected: boolean;
    bursts: number[];
    onCheer: () => void;
    moving: boolean;
}

export default function CheerCard({ room, connected, bursts, onCheer, moving }: Props) {
    return (
        <div className="cheer-card">
            <div className="card-top">
                <span>LIONS CHEER</span>
                <span className="live-label">
                    <i />
                    {connected ? 'LIVE' : '연결 중'}
                </span>
            </div>
            <div className="count-label">누적 응원</div>
            <div className="count-line">
                <strong aria-live="polite">
                    {room.cheers === null ? '—' : room.cheers.toLocaleString('ko-KR')}
                </strong>
                <span>회</span>
            </div>
            <div className="button-stage">
                <button
                    className="cheer-button"
                    type="button"
                    onClick={onCheer}
                    disabled={!connected}
                    aria-label="삼성 라이온즈에 응원 보내기"
                >
                    <span className="emblem-fallback" aria-hidden="true">
                        <Image src="/lions.svg" alt="" width={170} height={130} />
                    </span>
                    <GlassEmblem moving={moving} />
                </button>
                {bursts.map((id, index) => (
                    <span
                        key={id}
                        className="burst"
                        style={{ '--burst-x': `${((index % 3) - 1) * 35}px` } as CSSProperties}
                    >
                        <Icon name="heart" /> +1
                    </span>
                ))}
            </div>
            <p className="button-instruction">
                버튼을 눌러 응원하기 <Icon name="arrow-up-right" />
            </p>
            <div className="card-bottom">
                <span>삼성 라이온즈</span>
                <span>VAMOS LIONS!</span>
            </div>
        </div>
    );
}
