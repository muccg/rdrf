#
FROM muccg/rdrf-builder
MAINTAINER https://github.com/muccg/rdrf

# At build time changing these args allow us to use a local devpi mirror
# Unchanged, these defaults allow pip to behave as normal
ARG ARG_PIP_INDEX_URL="https://pypi.python.org/simple"
ARG ARG_PIP_TRUSTED_HOST="127.0.0.1"

# Runtime args
ENV PRODUCTION 0
ENV DEBUG 1
ENV PIP_INDEX_URL $ARG_PIP_INDEX_URL
ENV PIP_TRUSTED_HOST $ARG_PIP_TRUSTED_HOST
ENV NO_PROXY ${PIP_TRUSTED_HOST}

# Strictly speaking not needed as we mount over the top
# However let's make it explicit that we don't want /app from the build image
RUN rm -rf /app && mkdir -p /app

# # For dev we use root so we can shell in and do evil things
USER root
WORKDIR /app

RUN env | sort

# Add our python deps in multiple docker layers
# hgvs was failing due to lack of nose, hence the order
COPY rdrf/dev-requirements.txt /app/rdrf/
RUN pip install --upgrade -r rdrf/dev-requirements.txt
COPY rdrf/test-requirements.txt /app/rdrf/
RUN pip install --upgrade -r rdrf/test-requirements.txt

# Copy code and install the app
COPY . /app
RUN pip install --upgrade -e rdrf

EXPOSE 8000 9000 9001 9100 9101
VOLUME ["/app", "/data"]

ENV HOME /data
WORKDIR /data

# entrypoint shell script that by default starts runserver
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["runserver_plus"]
