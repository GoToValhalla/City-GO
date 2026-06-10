FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_ADMIN_API_TOKEN=
ENV VITE_ADMIN_API_TOKEN=$VITE_ADMIN_API_TOKEN

RUN VITE_API_BASE_URL="/api" VITE_USE_BACKEND=true npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
