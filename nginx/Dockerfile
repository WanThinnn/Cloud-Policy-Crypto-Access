FROM nginx

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/django.conf.template /etc/nginx/templates/django.conf.template

# Create directory for certificates
RUN mkdir -p /etc/nginx/certs

# Expose ports
EXPOSE 80 443

# Environment variables (PQC cert names) are passed via docker-compose.yml / .env
ENV DOMAIN_NAME=${DOMAIN_NAME}
ENV PQC_SSL_CERT_FILE=${PQC_SSL_CERT_FILE}
ENV PQC_SSL_KEY_FILE=${PQC_SSL_KEY_FILE}
ENV PQC_SSL_CA_FILE=${PQC_SSL_CA_FILE}
