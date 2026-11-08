export const MOVES = [
    { id: 'bounce', scene: 'jump', icon: 'sparkle', label: '폴짝폴짝' },
    { id: 'wave', scene: 'wave', icon: 'wave', label: '손 흔들기' },
    { id: 'spin', scene: 'cheer', icon: 'burst', label: '신나게 응원' },
] as const;

export type MoveId = (typeof MOVES)[number]['id'];
export type Dance = 'idle' | (typeof MOVES)[number]['scene'];
export interface RoomState {
    cheers: number | null;
    online: number | null;
}
export type ClientMessage = { type: 'cheer' } | { type: 'dance'; dance: MoveId };
export type ServerMessage =
    | { type: 'state' | 'cheer'; cheers: number; online: number }
    | { type: 'presence'; online: number }
    | { type: 'dance'; dance: MoveId; online: number };

export function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isMoveId(value: unknown): value is MoveId {
    return MOVES.some((move) => move.id === value);
}

function isCount(value: unknown): value is number {
    return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

export function parseServerMessage(raw: unknown): ServerMessage | null {
    if (!isRecord(raw) || !isCount(raw.online)) return null;
    switch (raw.type) {
        case 'state':
        case 'cheer':
            return isCount(raw.cheers)
                ? { type: raw.type, cheers: raw.cheers, online: raw.online }
                : null;
        case 'presence':
            return { type: 'presence', online: raw.online };
        case 'dance':
            return isMoveId(raw.dance)
                ? { type: 'dance', dance: raw.dance, online: raw.online }
                : null;
        default:
            return null;
    }
}

export function parseClientMessage(raw: unknown): ClientMessage | null {
    if (!isRecord(raw)) return null;
    if (raw.type === 'cheer') return { type: 'cheer' };
    return raw.type === 'dance' && isMoveId(raw.dance) ? { type: 'dance', dance: raw.dance } : null;
}

export function applyRoomMessage(state: RoomState, message: unknown): RoomState {
    if (!isRecord(message)) return state;
    return {
        cheers: isCount(message.cheers) ? message.cheers : state.cheers,
        online: isCount(message.online) ? message.online : state.online,
    };
}
