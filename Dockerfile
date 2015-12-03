#
FROM muccg/angelman:next_release
MAINTAINER https://bitbucket.org/ccgmurdoch/angelman/

ARG PIP_OPTS="--no-cache-dir"

USER root

# install python deps
COPY rdrf/*requirements.txt /app/rdrf/
WORKDIR /app
# hgvs was failing due to lack of nose, hence the order
RUN rm -rf /env && virtualenv /env
RUN /env/bin/pip ${PIP_OPTS} install -r rdrf/dev-requirements.txt
RUN /env/bin/pip ${PIP_OPTS} install -r rdrf/test-requirements.txt
RUN /env/bin/pip ${PIP_OPTS} install -r rdrf/runtime-requirements.txt

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy code and install the app
COPY . /app
RUN /env/bin/pip ${PIP_OPTS} install -e rdrf

EXPOSE 8000 9000 9001 9100 9101
VOLUME ["/app", "/data"]

ENV HOME /data
WORKDIR /data

# entrypoint shell script that by default starts runserver
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["runserver"]
