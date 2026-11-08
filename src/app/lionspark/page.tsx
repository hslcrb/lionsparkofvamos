import type { Metadata } from 'next';
import LionsparkWorld from '../../features/lionspark/lionspark-world';

export const metadata: Metadata = { title: '라팍월드' };

export default function LionsparkPage() {
    return <LionsparkWorld />;
}
