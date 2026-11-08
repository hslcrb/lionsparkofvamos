export interface Point {
    x: number;
    y: number;
}

export function isCinemaSwipe(start: Point | null, end: Point | null): boolean {
    if (!start || !end) return false;
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    return dx <= -70 && Math.abs(dx) > Math.abs(dy) * 1.4;
}
