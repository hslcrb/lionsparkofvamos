import type { Metadata } from 'next';
import App from '../../App';
import { MusicControl } from '../../components/music-provider';

export const metadata: Metadata = {
    title: '라이온즈 응원관',
    description: '삼성 라이온즈 응원 버튼과 응원관',
};
export default function MainPage() {
    return (
        <>
            <App />
            <MusicControl />
        </>
    );
}
