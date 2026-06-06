# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Copiar manifiestos primero para aprovechar cache de capas
COPY frontend/package.json frontend/package-lock.json* ./

# Instalar dependencias exactas del lockfile (sin devDeps opcionales para build)
RUN npm ci

# Copiar el resto del código fuente
COPY frontend/ .

# La variable VITE_API_URL se inyecta en build-time.
# En docker-compose se pasa como ARG; en producción se reemplaza en nginx.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build


# ── Stage 2: producción con nginx ─────────────────────────────────────────────
FROM nginx:1.27-alpine AS production

# Eliminar config por defecto de nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copiar nuestra config de SPA
COPY deploy/nginx.conf /etc/nginx/conf.d/app.conf

# Copiar artefactos de build
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
