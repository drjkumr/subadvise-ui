FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_SUBADVISE_API_URL=http://localhost:7071
ARG VITE_SUBADVISE_AI_API_URL=http://localhost:7072
ENV VITE_SUBADVISE_API_URL=${VITE_SUBADVISE_API_URL}
ENV VITE_SUBADVISE_AI_API_URL=${VITE_SUBADVISE_AI_API_URL}

RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
