FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Servir con nginx
FROM nginx:alpine

# Configuracion nginx para SPA + proxy al backend
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["/bin/sh", "-c", "RAW=$(awk '$1==\"nameserver\"{print $2; exit}' /etc/resolv.conf); if echo \"$RAW\" | grep -q ':'; then RESOLVER=\"[$RAW]\"; else RESOLVER=\"$RAW\"; fi && echo \"Using resolver: $RESOLVER\" && sed -i \"s|__RESOLVER__|$RESOLVER|g\" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
