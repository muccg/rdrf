# This Dockerfile won't be needed, but I've added it so I can
# make changes to RDRF 4.1.24 and then build images with my changes and push them to ECR.
# The images I've built are all in ECR they are tagged with 4.1.24 then a letter. 4.1.24-a, ..., 4.1.24-d
#
# Checked in this file just so that I make sure nothing is missed.
FROM muccg/rdrf:4.1.24

ADD docker-entrypoint.sh /app/
ADD rdrf/rdrf/initial_data/*.json /env/lib/python3.6/site-packages/rdrf/initial_data/

ENTRYPOINT /app/docker-entrypoint.sh
