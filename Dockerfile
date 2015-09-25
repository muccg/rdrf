#
FROM muccg/python-base:ubuntu14.04-2.7
MAINTAINER https://bitbucket.org/ccgmurdoch/fkrp/

ENV DEBIAN_FRONTEND noninteractive

#RUN rm /etc/apt/apt.conf.d/30proxy

# Project specific deps
RUN apt-get update && apt-get install -y --no-install-recommends \
  git \
  libpcre3 \
  libpcre3-dev \
  libpq-dev \
  libssl-dev \
  libyaml-dev \
  python-tk \
  sendmail \
  zlib1g-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN env --unset=DEBIAN_FRONTEND

# install python deps
COPY rdrf/*requirements.txt /app/rdrf/
WORKDIR /app
# hgvs was failing due to lack of nose, hence the order
RUN pip install -r rdrf/dev-requirements.txt
RUN pip install -r rdrf/test-requirements.txt
RUN pip install -r rdrf/runtime-requirements.txt

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy code and install the app
COPY . /app
RUN pip install -e rdrf

EXPOSE 8000 9000 9001 9100 9101
VOLUME ["/app", "/data"]

ENV HOME /data
WORKDIR /data

# entrypoint shell script that by default starts runserver
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["runserver"]
