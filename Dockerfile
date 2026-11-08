# Lions Park of VAMOS — multi-stage image.
#
#   docker compose up --build        → http://localhost:8080
#   docker build -t lionspark . && docker run -p 8080:8080 lionspark
#
# Stage 1 builds the static Next.js export. Stage 2 ships only the export and
# the dependency-free Node server, so the runtime image stays small and needs
# no npm install.

FROM node:22-alpine AS build
WORKDIR /app

# Install dependencies first so the layer cache survives source edits.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    PORT=8080 \
    HOST=0.0.0.0

COPY --from=build /app/out ./out
COPY server/standalone.mjs ./server/standalone.mjs

RUN addgroup -S lions && adduser -S lions -G lions && mkdir -p /data && chown -R lions:lions /data
USER lions

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

CMD ["node", "server/standalone.mjs"]
