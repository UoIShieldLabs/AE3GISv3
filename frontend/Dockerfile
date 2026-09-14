FROM node:22-alpine AS build

WORKDIR /app


COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Optional: only needed when the backend sets AE3GIS_INSTRUCTOR_TOKEN. Baked in
# at build time because the frontend has no sign-in screen.
ARG VITE_INSTRUCTOR_TOKEN=""
ENV VITE_INSTRUCTOR_TOKEN=$VITE_INSTRUCTOR_TOKEN

RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
