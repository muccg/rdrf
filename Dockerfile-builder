#
FROM muccg/rdrf-base
MAINTAINER https://github.com/muccg/rdrf

ENV PIP_NO_CACHE_DIR="off"
ENV PIP_INDEX_URL "https://pypi.python.org/simple"
ENV PIP_TRUSTED_HOST "127.0.0.1"
ENV NO_PROXY ${PIP_TRUSTED_HOST}

RUN env | sort

# Project specific deps
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  git \
  gzip \
  libpcre3-dev \
  libpq-dev \
  libssl-dev \
  libyaml-dev \
  unixodbc-dev \
  zlib1g-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY docker-entrypoint-build.sh /app/docker-entrypoint-build.sh

RUN mkdir -p /data \
    && /bin/chown ccg-user:ccg-user /data

VOLUME ["/data"]

ENV HOME /data
WORKDIR /data

ENTRYPOINT ["/app/docker-entrypoint-build.sh"]
CMD ["releasetarball"]
