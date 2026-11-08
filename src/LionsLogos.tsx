import React from 'react';
import Icon from './Icon';
import Image from 'next/image';

export default function LionsLogos({ className }: { className?: string }) {
    return (
        <div className={className}>
            <Image src="/lions.svg" alt="삼성 라이온즈" width={245} height={180} />
            <span aria-hidden="true">
                <Icon name="cross" />
            </span>
            <Image src="/vamos.svg" alt="2026 한국시리즈 VAMOS" width={245} height={180} />
        </div>
    );
}
