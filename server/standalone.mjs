// Lions Park of VAMOS — standalone Node.js host.
//
// Serves the static Next.js export in ./out and answers the /api/room
// WebSocket with the same message protocol as the Cloudflare CheerRoom, so a
// plain VPS, Docker, Railway, Fly.io or any Node host gets the full experience
// without a Cloudflare account.
//
//   npm run build && node server/standalone.mjs
//
// Environment:
//   PORT          HTTP port (default 8080)
//   HOST          bind address (default 0.0.0.0)
//   CHEERS_FILE   optional JSON file used to keep the cheer count across restarts
//
// No dependencies: only the Node.js standard library.

import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import {
    createReadStream,
    existsSync,
    mkdirSync,
    readFileSync,
    statSync,
    writeFileSync,
} from 'node:fs';
import { dirname, extname, join, normalize } from 'node:path';

const PORT = Number.parseInt(process.env.PORT ?? '8080', 10);
const HOST = process.env.HOST ?? '0.0.0.0';
const CHEERS_FILE = process.env.CHEERS_FILE ?? '';
const ROOT = new URL('../out/', import.meta.url).pathname;

const PAGES = new Map([
    ['/', '/index.html'],
    ['/main', '/main.html'],
    ['/lionspark', '/lionspark.html'],
    ['/418', '/418.html'],
]);

const MIME = new Map([
    ['.html', 'text/html; charset=utf-8'],
    ['.js', 'text/javascript; charset=utf-8'],
    ['.mjs', 'text/javascript; charset=utf-8'],
    ['.css', 'text/css; charset=utf-8'],
    ['.json', 'application/json; charset=utf-8'],
    ['.svg', 'image/svg+xml'],
    ['.png', 'image/png'],
    ['.jpg', 'image/jpeg'],
    ['.webp', 'image/webp'],
    ['.ico', 'image/x-icon'],
    ['.mp3', 'audio/mpeg'],
    ['.glb', 'model/gltf-binary'],
    ['.wasm', 'application/wasm'],
    ['.woff2', 'font/woff2'],
    ['.txt', 'text/plain; charset=utf-8'],
]);

const LONG_CACHE = new Set([
    '.js',
    '.css',
    '.png',
    '.jpg',
    '.webp',
    '.mp3',
    '.glb',
    '.wasm',
    '.woff2',
]);

// ---------------------------------------------------------------------------
// Cheer room (mirrors worker/cheer-room.ts)
// ---------------------------------------------------------------------------
const clients = new Set();
let cheers = 0;
let saveTimer = null;

if (CHEERS_FILE && existsSync(CHEERS_FILE)) {
    try {
        const data = JSON.parse(readFileSync(CHEERS_FILE, 'utf8'));
        if (Number.isSafeInteger(data.cheers) && data.cheers >= 0) cheers = data.cheers;
    } catch {
        /* a corrupt state file must not stop the server */
    }
}

function scheduleSave() {
    if (!CHEERS_FILE || saveTimer) return;
    saveTimer = setTimeout(() => {
        saveTimer = null;
        try {
            mkdirSync(dirname(CHEERS_FILE), { recursive: true });
            writeFileSync(CHEERS_FILE, JSON.stringify({ cheers }));
        } catch {
            /* read-only volumes simply skip persistence */
        }
    }, 400);
    saveTimer.unref?.();
}

function send(socket, event) {
    if (socket.destroyed || socket.writableEnded) return;
    const payload = Buffer.from(JSON.stringify(event));
    const length = payload.length;
    let header;
    if (length < 126) {
        header = Buffer.from([0x81, length]);
    } else if (length < 65536) {
        header = Buffer.alloc(4);
        header[0] = 0x81;
        header[1] = 126;
        header.writeUInt16BE(length, 2);
    } else {
        header = Buffer.alloc(10);
        header[0] = 0x81;
        header[1] = 127;
        header.writeBigUInt64BE(BigInt(length), 2);
    }
    socket.write(Buffer.concat([header, payload]));
}

function broadcast(event, except) {
    for (const socket of clients) if (socket !== except) send(socket, event);
}

const MOVE_IDS = new Set(['bounce', 'wave', 'spin']);

function parseClientMessage(raw) {
    if (typeof raw !== 'string' || raw.length > 256) return null;
    let value;
    try {
        value = JSON.parse(raw);
    } catch {
        return null;
    }
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return null;
    if (value.type === 'cheer') return { type: 'cheer' };
    if (value.type === 'dance' && MOVE_IDS.has(value.dance))
        return { type: 'dance', dance: value.dance };
    return null;
}

function handleMessage(socket, raw) {
    const message = parseClientMessage(raw);
    if (!message) return;
    const now = Date.now();
    if (message.type === 'cheer') {
        if (now - (socket.cheerAt ?? 0) < 250) return;
        socket.cheerAt = now;
        cheers += 1;
        scheduleSave();
        broadcast({ type: 'cheer', cheers, online: clients.size });
    } else {
        if (now - (socket.danceAt ?? 0) < 500) return;
        socket.danceAt = now;
        broadcast({ type: 'dance', dance: message.dance, online: clients.size });
    }
}

// ---------------------------------------------------------------------------
// Static files
// ---------------------------------------------------------------------------
function safePath(pathname) {
    const decoded = decodeURIComponent(pathname.split('?')[0]);
    const normalized = normalize(decoded).replace(/^(\.\.[/\\])+/, '');
    return join(ROOT, normalized);
}

function sendFile(request, response, path, status = 200) {
    let stat;
    try {
        stat = statSync(path);
    } catch {
        return false;
    }
    if (!stat.isFile()) return false;
    const type = MIME.get(extname(path).toLowerCase()) ?? 'application/octet-stream';
    const isHtml = type.startsWith('text/html');
    response.writeHead(status, {
        'content-type': type,
        'content-length': stat.size,
        'cache-control': isHtml
            ? 'no-cache'
            : LONG_CACHE.has(extname(path).toLowerCase())
              ? 'public, max-age=31536000, immutable'
              : 'public, max-age=3600',
        'x-content-type-options': 'nosniff',
        'referrer-policy': 'strict-origin-when-cross-origin',
    });
    if (request.method === 'HEAD') {
        response.end();
        return true;
    }
    createReadStream(path).pipe(response);
    return true;
}

const server = createServer((request, response) => {
    const url = new URL(request.url ?? '/', `http://${request.headers.host ?? 'localhost'}`);
    if (url.pathname === '/api/room') {
        response.writeHead(426, { 'content-type': 'text/plain; charset=utf-8' });
        response.end('WebSocket required');
        return;
    }
    if (url.pathname === '/healthz') {
        response.writeHead(200, { 'content-type': 'application/json' });
        response.end(JSON.stringify({ ok: true, cheers, online: clients.size }));
        return;
    }
    const path = url.pathname.replace(/\/+$/, '') || '/';
    const page = PAGES.get(path);
    if (path === '/' || path === '/418' || page) {
        if (request.method !== 'GET' && request.method !== 'HEAD') {
            response.writeHead(405, {
                allow: 'GET, HEAD',
                'content-type': 'text/plain; charset=utf-8',
            });
            response.end('Method not allowed');
            return;
        }
        const file = join(ROOT, page ?? '/index.html');
        if (sendFile(request, response, file, path === '/418' ? 418 : 200)) return;
        response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
        response.end('Not found');
        return;
    }
    if (request.method !== 'GET' && request.method !== 'HEAD') {
        response.writeHead(405, {
            allow: 'GET, HEAD',
            'content-type': 'text/plain; charset=utf-8',
        });
        response.end('Method not allowed');
        return;
    }
    const asset = safePath(url.pathname);
    if (asset.startsWith(ROOT) && sendFile(request, response, asset)) return;
    if (request.headers.accept?.includes('text/html')) {
        const notFound = join(ROOT, '404.html');
        if (sendFile(request, response, notFound, 404)) return;
    }
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('Not found');
});

server.on('upgrade', (request, socket) => {
    try {
        const url = new URL(request.url ?? '/', `http://${request.headers.host ?? 'localhost'}`);
        if (url.pathname !== '/api/room') {
            socket.destroy();
            return;
        }
        const origin = request.headers.origin;
        if (
            origin &&
            origin !== `http://${request.headers.host}` &&
            origin !== `https://${request.headers.host}`
        ) {
            socket.write('HTTP/1.1 403 Forbidden\r\n\r\n');
            socket.destroy();
            return;
        }
        const key = request.headers['sec-websocket-key'];
        if (typeof key !== 'string') {
            socket.destroy();
            return;
        }
        const accept = createHash('sha1')
            .update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
            .digest('base64');
        socket.write(
            'HTTP/1.1 101 Switching Protocols\r\n' +
                'Upgrade: websocket\r\n' +
                'Connection: Upgrade\r\n' +
                `Sec-WebSocket-Accept: ${accept}\r\n\r\n`,
        );
        socket.cheerAt = 0;
        socket.danceAt = 0;
        socket.setNoDelay(true);
        clients.add(socket);
        send(socket, { type: 'state', cheers, online: clients.size });
        broadcast({ type: 'presence', online: clients.size }, socket);

        let buffer = Buffer.alloc(0);
        socket.on('data', (chunk) => {
            buffer = Buffer.concat([buffer, chunk]);
            while (buffer.length >= 2) {
                const fin = (buffer[0] & 0x80) !== 0;
                const opcode = buffer[0] & 0x0f;
                const masked = (buffer[1] & 0x80) !== 0;
                let length = buffer[1] & 0x7f;
                let offset = 2;
                if (length === 126) {
                    if (buffer.length < 4) return;
                    length = buffer.readUInt16BE(2);
                    offset = 4;
                } else if (length === 127) {
                    if (buffer.length < 10) return;
                    length = Number(buffer.readBigUInt64BE(2));
                    offset = 10;
                }
                if (length > 1_048_576) {
                    socket.destroy();
                    return;
                }
                const maskOffset = offset;
                if (masked) offset += 4;
                if (buffer.length < offset + length) return;
                const payload = Buffer.from(buffer.subarray(offset, offset + length));
                if (masked) {
                    const mask = buffer.subarray(maskOffset, maskOffset + 4);
                    for (let i = 0; i < payload.length; i += 1) payload[i] ^= mask[i % 4];
                }
                buffer = buffer.subarray(offset + length);
                if (opcode === 0x8) {
                    socket.end();
                    return;
                }
                if (opcode === 0x9) {
                    socket.write(Buffer.from([0x8a, payload.length, ...payload]));
                    continue;
                }
                if (opcode === 0x1 && fin) handleMessage(socket, payload.toString('utf8'));
            }
        });
        const drop = () => {
            if (!clients.delete(socket)) return;
            broadcast({ type: 'presence', online: clients.size });
        };
        socket.on('close', drop);
        socket.on('error', drop);
    } catch (error) {
        console.error('upgrade failed', error);
        socket.destroy();
    }
});

server.listen(PORT, HOST, () => {
    console.log(`Lions Park of VAMOS on http://${HOST}:${PORT}`);
    console.log(`  static root: ${ROOT}`);
    console.log(`  cheer persistence: ${CHEERS_FILE || 'memory only'}`);
});
