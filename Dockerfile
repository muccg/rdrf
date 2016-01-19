#
FROM muccg/rdrf:next_release
MAINTAINER https://github.com/muccg/rdrf

ARG PIP_OPTS="--no-cache-dir"

ENV DEPLOYMENT dev
ENV PRODUCTION 0
ENV DEBUG 1

USER root
WORKDIR /app

# install python deps
COPY rdrf/*requirements.txt /app/rdrf/

# hgvs was failing due to lack of nose, hence the order
RUN pip freeze
RUN pip ${PIP_OPTS} uninstall -y django-rdrf
RUN pip ${PIP_OPTS} install --upgrade -r rdrf/dev-requirements.txt
RUN pip ${PIP_OPTS} install --upgrade -r rdrf/test-requirements.txt
RUN pip ${PIP_OPTS} install --upgrade -r rdrf/runtime-requirements.txt

# Copy code and install the app
COPY . /app
RUN pip ${PIP_OPTS} install --upgrade -e rdrf

EXPOSE 8000 9000 9001 9100 9101
VOLUME ["/app", "/data"]

ENV HOME /data
WORKDIR /data

# entrypoint shell script that by default starts runserver
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["runserver"]
