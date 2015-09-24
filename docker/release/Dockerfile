#
FROM muccg/python-base:ubuntu14.04-2.7
MAINTAINER https://bitbucket.org/ccgmurdoch/rdrf/

ENV DEBIAN_FRONTEND noninteractive

# Project specific deps
RUN apt-get update && apt-get install -y \
  git \
  libpcre3 \
  libpcre3-dev \
  libpq-dev \
  libssl-dev \
  libyaml-dev \
  zlib1g-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN env --unset=DEBIAN_FRONTEND

WORKDIR /app
RUN git clone --depth=1 --branch=1.0.9 https://bitbucket.org/ccgmurdoch/rdrf.git .

# install python deps
# hgvs was failing due to lack of nose, hence the order
RUN pip install nose
RUN pip install -r rdrf/runtime-requirements.txt
RUN pip install -e rdrf

EXPOSE 9100 9101
VOLUME ["/data"]

RUN cp docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Drop privileges, set home for ccg-user
USER ccg-user
ENV HOME /data
WORKDIR /data

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uwsgi"]
