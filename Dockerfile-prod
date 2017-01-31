# 
FROM muccg/rdrf-base
MAINTAINER https://github.com/muccg/rdrf/

ARG ARG_BUILD_VERSION

ENV BUILD_VERSION $ARG_BUILD_VERSION

RUN env | sort

RUN mkdir -p /data \
    && /bin/chown ccg-user:ccg-user /data

ADD build/${PROJECT_NAME}-${BUILD_VERSION}.tar.gz /

EXPOSE 9100 9101
VOLUME ["/data"]

# Drop privileges, set home for ccg-user
USER ccg-user
ENV HOME /data
WORKDIR /data

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uwsgi"]
