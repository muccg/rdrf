#!/usr/bin/sh

# -----------------------------------------------------------------------------
# Intended to be used as; ./export_zip.sh REGISTRY_CODE
# i.e. Argument 1 must be the registry code.
# Further, the assumption is made that the YAML has been imported, the users
# swapped over, and at least one model patient is present.
# -----------------------------------------------------------------------------

docker exec -it rdrf_runserver_1 /app/docker-entrypoint.sh \
  django-admin export registry --registry-code $1

