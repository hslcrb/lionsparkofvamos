import test from 'node:test';
import assert from 'node:assert/strict';
import { handleRequest, type Env } from './index';
import { CheerRoom } from './cheer-room';

function environment(): Env {
    return {
        ASSETS: {
            fetch: async (request: Request) => {
                const path = new URL(request.url).pathname;
                const exists = [
                    '/index.html',
                    '/main.html',
                    '/lionspark.html',
                    '/418.html',
                    '/404.html',
                    '/lions.svg',
                    '/main.txt',
                ].includes(path);
                return new Response(path, { status: exists ? 200 : 404 });
            },
        },
    } as unknown as Env;
}

test('direct routes serve the corresponding Next.js export with the correct status', async () => {
    for (const [path, file, status] of [
        ['/', '/index.html', 200],
        ['/main', '/main.html', 200],
        ['/main/', '/main.html', 200],
        ['/lionspark', '/lionspark.html', 200],
        ['/418', '/418.html', 418],
        ['/418/', '/418.html', 418],
        ['/unknown', '/404.html', 404],
    ] as const) {
        const response = await handleRequest(
            new Request(`https://example.com${path}`, { headers: { Accept: 'text/html' } }),
            environment(),
        );
        assert.equal(response.status, status, path);
        assert.equal(await response.text(), file, path);
    }
});

test('assets, Next navigation payloads and missing APIs bypass HTML fallbacks', async () => {
    for (const [path, status] of [
        ['/lions.svg', 200],
        ['/main.txt', 200],
        ['/missing.js', 404],
        ['/api/missing', 404],
    ] as const) {
        const response = await handleRequest(
            new Request(`https://example.com${path}`),
            environment(),
        );
        assert.equal(response.status, status);
        assert.equal(await response.text(), path);
    }
});

test('HEAD returns no body and unsupported page methods are rejected', async () => {
    const head = await handleRequest(
        new Request('https://example.com/main', { method: 'HEAD' }),
        environment(),
    );
    assert.equal(head.status, 200);
    assert.equal(await head.text(), '');
    const post = await handleRequest(
        new Request('https://example.com/main', { method: 'POST' }),
        environment(),
    );
    assert.equal(post.status, 405);
});

test('cross-origin room connections are rejected before the Durable Object is called', async () => {
    const response = await handleRequest(
        new Request('https://example.com/api/room', { headers: { Origin: 'https://other.com' } }),
        environment(),
    );
    assert.equal(response.status, 403);
});

test('a cheer increments persisted count, broadcasts, and throttles repeated messages', async () => {
    let count = 7;
    let attachment: unknown = {};
    const sent: unknown[] = [];
    const socket = {
        send: (value: string) => sent.push(JSON.parse(value)),
        serializeAttachment: (value: unknown) => {
            attachment = value;
        },
        deserializeAttachment: () => attachment,
    } as unknown as WebSocket;
    const state = {
        storage: {
            sql: {
                exec(query: string) {
                    if (query.startsWith('UPDATE')) count++;
                    return { one: () => ({ count }) };
                },
            },
        },
        getWebSockets: () => [socket],
        blockConcurrencyWhile: (callback: () => Promise<void>) => callback(),
    } as unknown as DurableObjectState;
    const room = new CheerRoom(state);
    await room.webSocketMessage(socket, JSON.stringify({ type: 'cheer' }));
    await room.webSocketMessage(socket, JSON.stringify({ type: 'cheer' }));
    await room.webSocketMessage(socket, 'null');
    await room.webSocketMessage(socket, JSON.stringify({ type: 'dance', dance: 'unknown' }));
    assert.equal(count, 8);
    assert.deepEqual(sent, [{ type: 'cheer', cheers: 8, online: 1 }]);
});

test('closing a room connection completes the close handshake', async () => {
    let closed = false;
    const socket = {
        close: () => {
            closed = true;
        },
    } as unknown as WebSocket;
    const state = {
        storage: { sql: { exec: () => ({}) } },
        getWebSockets: () => [],
        blockConcurrencyWhile: (callback: () => Promise<void>) => callback(),
    } as unknown as DurableObjectState;
    const room = new CheerRoom(state);
    await room.webSocketClose(socket);
    assert.equal(closed, true);
});
