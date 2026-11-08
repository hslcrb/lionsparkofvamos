import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';

const origin = 'http://127.0.0.1:8787';
for (let attempt = 0; ; attempt++) {
    try {
        await fetch(origin);
        break;
    } catch (error) {
        if (attempt >= 60) throw error;
        await delay(250);
    }
}
for (const [path, status, content] of [
    ['/', 200, '라팍월드 들어가기'],
    ['/main', 200, '가자 삼성!'],
    ['/lionspark', 200, '대구 삼성 라이온즈파크'],
    ['/418', 418, '주전자'],
    ['/missing-page', 404, '찾을 수 없어요'],
] as const) {
    const response = await fetch(`${origin}${path}`, { headers: { Accept: 'text/html' } });
    assert.equal(response.status, status, path);
    assert.ok((await response.text()).includes(content), path);
}
const payload = await fetch(`${origin}/main.txt`);
assert.equal(payload.status, 200, 'Next.js navigation payload');
const audio = await fetch(`${origin}/my-lions.mp3`, { headers: { Range: 'bytes=0-1023' } });
assert.ok(audio.ok);
assert.match(audio.headers.get('content-type') ?? '', /audio/);
await audio.body?.cancel();

function openRoom() {
    const socket = new WebSocket(origin.replace('http', 'ws') + '/api/room');
    const events: Record<string, unknown>[] = [];
    socket.addEventListener('message', (event) => {
        events.push(JSON.parse(String(event.data)));
    });
    return { socket, events };
}
async function until(check: () => boolean) {
    for (let attempt = 0; !check(); attempt++) {
        if (attempt > 100) throw new Error('Timed out waiting for a room event');
        await delay(50);
    }
}
const first = openRoom();
const second = openRoom();
try {
    await until(
        () =>
            first.events.some((event) => event.type === 'state') &&
            second.events.some((event) => event.type === 'state'),
    );
    const state = first.events.find((event) => event.type === 'state');
    assert.equal(typeof state?.cheers, 'number');
    first.socket.send(JSON.stringify({ type: 'cheer' }));
    await until(() => second.events.some((event) => event.type === 'cheer'));
    const cheer = second.events.find((event) => event.type === 'cheer');
    assert.equal(cheer?.cheers, (state!.cheers as number) + 1);
    first.socket.send(JSON.stringify({ type: 'dance', dance: 'wave' }));
    await until(() =>
        second.events.some((event) => event.type === 'dance' && event.dance === 'wave'),
    );
} finally {
    first.socket.close();
    second.socket.close();
}
console.log(
    'Verified exported routes, error status, audio, navigation payload and two-client room sharing.',
);
