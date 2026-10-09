# Egress proxy: api.anthropic.com으로만 전달하는 TLS 종료 nginx.
# 일반 http{} reverse proxy — stream module 필요 없음.
FROM nginx:alpine

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 443 80

CMD ["nginx", "-g", "daemon off;"]
