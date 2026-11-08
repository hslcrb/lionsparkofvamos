// 하위 경로 배포용 자산 경로 / Asset paths for sub-path deployments
//
// GitHub Pages 프로젝트 사이트처럼 /저장소/ 아래에 올릴 때는
// NEXT_PUBLIC_BASE_PATH=/저장소 로 빌드합니다.
export const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH ?? '').replace(/\/+$/, '');

export function assetPath(path: string): string {
    if (!path.startsWith('/')) return path;
    return `${BASE_PATH}${path}`;
}
