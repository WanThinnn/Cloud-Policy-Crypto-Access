FROM openquantumsafe/nginx

# Copy custom nginx configuration (OQS uses /opt/nginx/)
COPY nginx.conf /opt/nginx/conf/nginx.conf
COPY conf.d/django.conf.template /opt/nginx/conf/templates/django.conf.template

# Create directory for certificates
RUN mkdir -p /opt/nginx/certs /opt/nginx/conf/conf.d

# Install envsubst (gettext) for template processing
USER root
RUN apk add --no-cache gettext

# Expose ports
EXPOSE 80 443

# Default environment variables (PQC cert names)
ENV DOMAIN_NAME=cloudsafe.cyberfortress.local
ENV PQC_SSL_CERT_FILE=_.pq-cyberfortress.local.crt
ENV PQC_SSL_KEY_FILE=_.pq-cyberfortress.local.key
ENV PQC_SSL_CA_FILE=pq-CyberFortress-RootCA.crt

# Use envsubst to replace environment variables in config template at startup
# Then start nginx with the OQS-specific binary path
CMD ["/bin/sh", "-c", "envsubst '${DOMAIN_NAME} ${PQC_SSL_CERT_FILE} ${PQC_SSL_KEY_FILE} ${PQC_SSL_CA_FILE}' < /opt/nginx/conf/templates/django.conf.template > /opt/nginx/conf/conf.d/django.conf && /opt/nginx/sbin/nginx -g 'daemon off;'"]
