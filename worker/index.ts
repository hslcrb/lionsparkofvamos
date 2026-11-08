export { CheerRoom } from './cheer-room';
export interface Env {
    ASSETS: Fetcher;
    CHEER_ROOM: DurableObjectNamespace;
}

const pages = new Map([
    ['/', '/index.html'],
    ['/main', '/main.html'],
    ['/lionspark', '/lionspark.html'],
    ['/418', '/418.html'],
]);

export async function handleRequest(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === '/api/room') {
        const origin = request.headers.get('Origin');
        if (origin && origin !== url.origin) return new Response('Forbidden', { status: 403 });
        return env.CHEER_ROOM.getByName('cinema').fetch(request);
    }
    const path = url.pathname.replace(/\/+$/, '') || '/';
    const page = pages.get(path);
    if (!page) {
        const asset = await env.ASSETS.fetch(request);
        if (
            asset.status !== 404 ||
            !request.headers.get('Accept')?.includes('text/html') ||
            path.startsWith('/api/')
        )
            return asset;
    }
    if (page || request.headers.get('Accept')?.includes('text/html')) {
        if (request.method !== 'GET' && request.method !== 'HEAD') {
            return new Response('Method not allowed', {
                status: 405,
                headers: { Allow: 'GET, HEAD' },
            });
        }
        const assetUrl = new URL(page ?? '/404.html', url);
        const response = await env.ASSETS.fetch(new Request(assetUrl, request));
        if (!response.ok) return response;
        const status = path === '/418' ? 418 : page ? 200 : 404;
        return new Response(request.method === 'HEAD' ? null : response.body, {
            status,
            headers: response.headers,
        });
    }
    return env.ASSETS.fetch(request);
}

export default { fetch: handleRequest } satisfies ExportedHandler<Env>;
