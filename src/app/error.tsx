'use client';
import { UnavailablePage } from '../EntryPages';
export default function ErrorPage({ reset }: { reset: () => void }) {
    return <UnavailablePage retry={reset} />;
}
