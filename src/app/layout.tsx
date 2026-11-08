import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import { MusicProvider } from '../components/music-provider';
import '../style.css';
import '../entry-pages.css';
import '../cinema.css';

export const metadata: Metadata = {
    title: { default: '더 라이온즈 버튼', template: '%s · 더 라이온즈 버튼' },
    description: '삼성 라이온즈 팬들의 작고 포근한 응원관. 함께 응원을 모아 우승을 기원해요.',
};
export const viewport: Viewport = { themeColor: '#1552d7' };

export default function RootLayout({ children }: { children: ReactNode }) {
    return (
        <html lang="ko">
            <body>
                <MusicProvider>{children}</MusicProvider>
            </body>
        </html>
    );
}
