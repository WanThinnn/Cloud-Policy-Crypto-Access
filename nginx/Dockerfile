FROM nginx:alpine

# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/django.conf.template /etc/nginx/templates/django.conf.template

# Create directory for certificates
RUN mkdir -p /etc/nginx/certs

# Expose ports
EXPOSE 80 443

# Default environment variables
ENV DOMAIN_NAME=cloudsafe.cyberfortress.local
ENV SSL_CERT_FILE=_.cyberfortress.local.crt
ENV SSL_KEY_FILE=_.cyberfortress.local.key
ENV SSL_CA_FILE=CyberFortress-RootCA.crt

# Use envsubst to replace environment variables in config template at startup
CMD ["/bin/sh", "-c", "envsubst '${DOMAIN_NAME} ${SSL_CERT_FILE} ${SSL_KEY_FILE} ${SSL_CA_FILE}' < /etc/nginx/templates/django.conf.template > /etc/nginx/conf.d/django.conf && nginx -g 'daemon off;'"]
