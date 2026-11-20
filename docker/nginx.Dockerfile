FROM node:22-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=frontend /app/dist/ /usr/share/nginx/html/
COPY nginx/http.conf /etc/nginx/templates/default.conf.template
COPY nginx/site.conf /etc/nginx/bilim-site.conf
