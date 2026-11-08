'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ClientMessage } from '../room';

export function useCheerBursts(send: (message: ClientMessage) => boolean) {
    const [bursts, setBursts] = useState<number[]>([]);
    const burstId = useRef(0);
    const lastCheer = useRef(0);
    const timers = useRef(new Set<ReturnType<typeof setTimeout>>());
    useEffect(() => {
        const pending = timers.current;
        return () => {
            for (const timer of pending) clearTimeout(timer);
        };
    }, []);
    const cheer = useCallback(() => {
        const now = Date.now();
        if (now - lastCheer.current < 250 || !send({ type: 'cheer' })) return;
        lastCheer.current = now;
        const id = ++burstId.current;
        setBursts((current) => [...current.slice(-8), id]);
        const timer = setTimeout(() => {
            timers.current.delete(timer);
            setBursts((current) => current.filter((item) => item !== id));
        }, 1800);
        timers.current.add(timer);
    }, [send]);
    return { bursts, cheer };
}
