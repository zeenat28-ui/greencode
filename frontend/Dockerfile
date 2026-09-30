# React + Vite frontend: build once, serve as static files.
#
# The `npm run build` script is `tsc --noEmit && vite build`, so a TypeScript
# error fails the image build instead of shipping a broken bundle to users.
FROM node:20-alpine AS build

WORKDIR /app

# Copy manifests first so `npm ci` is cached until dependencies actually change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/healthz >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
