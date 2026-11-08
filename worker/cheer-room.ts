import { parseClientMessage } from '../src/room';
interface SocketAttachment {
    cheerAt?: number;
    danceAt?: number;
}
export class CheerRoom {
    constructor(private state: DurableObjectState) {
        state.blockConcurrencyWhile(async () => {
            state.storage.sql.exec(
                'CREATE TABLE IF NOT EXISTS cheers (id INTEGER PRIMARY KEY, count INTEGER NOT NULL)',
            );
            state.storage.sql.exec('INSERT OR IGNORE INTO cheers (id, count) VALUES (1, 0)');
        });
    }

    sockets(except?: WebSocket) {
        return this.state.getWebSockets().filter((socket) => socket !== except);
    }

    broadcast(event: unknown, except?: WebSocket) {
        const message = JSON.stringify(event);
        for (const socket of this.sockets(except)) {
            try {
                socket.send(message);
            } catch {
                /* A closing connection can disappear between events. */
            }
        }
    }

    async fetch(request: Request): Promise<Response> {
        if (request.headers.get('Upgrade')?.toLowerCase() !== 'websocket') {
            return new Response('WebSocket required', { status: 426 });
        }
        const pair = new WebSocketPair();
        const client = pair[0];
        const server = pair[1];
        this.state.acceptWebSocket(server);
        server.serializeAttachment({});
        const online = this.sockets().length;
        const cheers = this.state.storage.sql
            .exec<{ count: number }>('SELECT count FROM cheers WHERE id = 1')
            .one().count;
        server.send(JSON.stringify({ type: 'state', cheers, online }));
        this.broadcast({ type: 'presence', online }, server);
        return new Response(null, { status: 101, webSocket: client });
    }

    async webSocketMessage(socket: WebSocket, raw: string | ArrayBuffer) {
        if (typeof raw !== 'string' || raw.length > 256) return;
        let parsed: unknown;
        try {
            parsed = JSON.parse(raw);
        } catch {
            return;
        }
        const message = parseClientMessage(parsed);
        if (!message) return;
        const attachment = (socket.deserializeAttachment() as SocketAttachment | null) || {};
        const now = Date.now();
        const online = this.sockets().length;
        if (message.type === 'cheer' && now - (attachment.cheerAt || 0) >= 250) {
            attachment.cheerAt = now;
            socket.serializeAttachment(attachment);
            const cheers = this.state.storage.sql
                .exec<{ count: number }>(
                    'UPDATE cheers SET count = count + 1 WHERE id = 1 RETURNING count',
                )
                .one().count;
            this.broadcast({ type: 'cheer', cheers, online });
        } else if (message.type === 'dance' && now - (attachment.danceAt || 0) >= 500) {
            attachment.danceAt = now;
            socket.serializeAttachment(attachment);
            this.broadcast({ type: 'dance', dance: message.dance, online });
        }
    }

    async webSocketClose(socket: WebSocket) {
        socket.close(1000, 'Client disconnected');
        this.broadcast({ type: 'presence', online: this.sockets(socket).length }, socket);
    }

    async webSocketError(socket: WebSocket) {
        socket.close(1011, 'Connection error');
        this.broadcast({ type: 'presence', online: this.sockets(socket).length }, socket);
    }
}
