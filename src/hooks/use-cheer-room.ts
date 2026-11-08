'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
    applyRoomMessage,
    MOVES,
    parseServerMessage,
    type ClientMessage,
    type Dance,
    type MoveId,
    type RoomState,
} from '../room';

export function useCheerRoom() {
    const [room, setRoom] = useState<RoomState>({ cheers: null, online: null });
    const [connected, setConnected] = useState(false);
    const [dance, setDance] = useState<Dance>('idle');
    const [activeMove, setActiveMove] = useState<MoveId | null>(null);
    const socket = useRef<WebSocket | null>(null);
    const danceTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
    const lastDance = useRef(0);

    const playMove = useCallback((id: MoveId) => {
        const move = MOVES.find((item) => item.id === id);
        if (!move) return;
        clearTimeout(danceTimer.current);
        setActiveMove(id);
        setDance(move.scene);
        danceTimer.current = setTimeout(() => {
            setDance('idle');
            setActiveMove(null);
        }, 5000);
    }, []);

    useEffect(() => {
        let retry: ReturnType<typeof setTimeout> | undefined;
        let closed = false;
        function connect() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${location.host}/api/room`);
            socket.current = ws;
            ws.onopen = () => {
                if (!closed) setConnected(true);
            };
            ws.onmessage = (event) => {
                if (closed || typeof event.data !== 'string') return;
                try {
                    const message = parseServerMessage(JSON.parse(event.data));
                    if (!message) return;
                    setRoom((previous) => applyRoomMessage(previous, message));
                    if (message.type === 'dance') playMove(message.dance);
                } catch {
                    /* Ignore malformed messages from the network. */
                }
            };
            ws.onclose = () => {
                if (closed) return;
                setConnected(false);
                retry = setTimeout(connect, 3000);
            };
            ws.onerror = () => ws.close();
        }
        connect();
        return () => {
            closed = true;
            clearTimeout(retry);
            clearTimeout(danceTimer.current);
            socket.current?.close();
            socket.current = null;
        };
    }, [playMove]);

    const send = useCallback((message: ClientMessage): boolean => {
        const ws = socket.current;
        if (ws?.readyState !== WebSocket.OPEN) return false;
        try {
            ws.send(JSON.stringify(message));
            return true;
        } catch {
            return false;
        }
    }, []);

    const chooseMove = useCallback(
        (id: MoveId) => {
            const now = Date.now();
            if (now - lastDance.current < 500) return;
            lastDance.current = now;
            playMove(id);
            send({ type: 'dance', dance: id });
        },
        [playMove, send],
    );

    return { room, connected, dance, activeMove, chooseMove, send };
}
