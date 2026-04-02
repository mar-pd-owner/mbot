FROM node:18-slim

RUN apt-get update && apt-get install -y \
    chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN mkdir -p /app/data/logs

ENV NODE_ENV=production
ENV PORT=8000

EXPOSE 8000

CMD node server.js & node bot.js
