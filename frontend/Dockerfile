FROM node:20-alpine

WORKDIR /app

COPY package.json bun.lockb* package-lock.json* ./
RUN npm install --legacy-peer-deps 2>/dev/null || npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
