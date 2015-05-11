#
FROM muccg/python-base:ubuntu14.04-2.7
MAINTAINER ccg <devops@ccg.murdoch.edu.au>

ENV DEBIAN_FRONTEND noninteractive

# Project specific deps
RUN apt-get update && apt-get install -y \
  git \
  libpcre3 \
  libpcre3-dev \
  libpq-dev \
  libssl-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN env --unset=DEBIAN_FRONTEND

WORKDIR /app
RUN git clone --depth=1 --branch=0.8.20 https://bitbucket.org/ccgmurdoch/rdrf.git .

WORKDIR /app/rdrf
RUN pip install --process-dependency-links .

EXPOSE 9100 9101
VOLUME ["/data"]

RUN chmod +x /app/docker-entrypoint.sh

# Drop privileges, set home for ccg-user
USER ccg-user
ENV HOME /data
WORKDIR /data

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uwsgi"]
