# Solwin Frontend — static build served by nginx (SPA + API reverse proxy)
# Upstream API locations are injected at container start:
#   BACKEND_SERVICE_URL (default http://backend:8001)
#   DATA_SERVICE_URL    (default http://data-api:8000)
# so the same image works in docker compose (service names) and Cloud Run
# (service URLs).

FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Same-origin API bases: nginx proxies /api and /data-api to the backends.
ENV VITE_API_BASE_URL=/api/v1 \
    VITE_DATA_API_BASE_URL=/data-api

RUN npm run build

FROM nginx:1.27-alpine AS runtime

RUN addgroup -S app && adduser -S app -G app

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# envsubst runs at container start over /etc/nginx/templates/*.template
# (nginx image built-in mechanism), writing /etc/nginx/conf.d/default.conf.
ENV BACKEND_SERVICE_URL=http://backend:8001 \
    DATA_SERVICE_URL=http://data-api:8000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
