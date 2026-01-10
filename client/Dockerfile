FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY package.json ./
COPY server.js ./
RUN npm install --production express http-proxy-middleware
EXPOSE 4173
ENV PORT=4173
ENV API_TARGET=http://api:8000
CMD ["node", "server.js"]
