# Solwin Frontend — static build served by nginx (SPA + API reverse proxy)

FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Same-origin API bases: nginx proxies /api and /data-api to the backends.
# Works identically on Cloud Run, GKE, or any container host.
ENV VITE_API_BASE_URL=/api/v1 \
    VITE_DATA_API_BASE_URL=/data-api

RUN npm run build

FROM nginx:1.27-alpine AS runtime

RUN addgroup -S app && adduser -S app -G app

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
