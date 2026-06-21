FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_ADMIN_API_TOKEN=
ARG VITE_BUILD_SHA=local
ARG VITE_BUILD_RUN_ID=local
ARG VITE_BUILD_RUN_NUMBER=local
ARG VITE_BUILD_TIME=local
ENV VITE_ADMIN_API_TOKEN=$VITE_ADMIN_API_TOKEN
ENV VITE_BUILD_SHA=$VITE_BUILD_SHA
ENV VITE_BUILD_RUN_ID=$VITE_BUILD_RUN_ID
ENV VITE_BUILD_RUN_NUMBER=$VITE_BUILD_RUN_NUMBER
ENV VITE_BUILD_TIME=$VITE_BUILD_TIME

RUN VITE_API_BASE_URL="/api" VITE_USE_BACKEND=true npm run build

FROM nginx:alpine

ARG VITE_BUILD_SHA=local
ARG VITE_BUILD_RUN_ID=local
ARG VITE_BUILD_RUN_NUMBER=local
ARG VITE_BUILD_TIME=local

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN printf '{"sha":"%s","run_id":"%s","run_number":"%s","time":"%s"}\n' \
    "$VITE_BUILD_SHA" "$VITE_BUILD_RUN_ID" "$VITE_BUILD_RUN_NUMBER" "$VITE_BUILD_TIME" \
    > /usr/share/nginx/html/build.json

EXPOSE 80