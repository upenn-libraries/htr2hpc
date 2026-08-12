FROM docker.io/library/node:12-alpine AS frontend

RUN apk update && apk add git

ENV ESCRIPTORIUM_SRC=/escriptorium-src
RUN git clone https://gitlab.com/scripta/escriptorium.git ${ESCRIPTORIUM_SRC} && \
    cd ${ESCRIPTORIUM_SRC} && \
    git checkout v1.0.1

RUN cp -r ${ESCRIPTORIUM_SRC}/front /build
WORKDIR /build
RUN npm ci && npm run production

# Pull official base image
FROM registry.gitlab.com/scripta/escriptorium:v1.0.1 AS escriptorium
#FROM registry.gitlab.com/scripta/escriptorium/base:kraken529 AS escriptorium

# try to autodetect number of cpus available
# ENV NGINX_WORKER_PROCESSES auto

ARG VERSION_DATE="passthistobuildcmd"
ENV VERSION_DATE=$VERSION_DATE
ENV FRONTEND_DIR=/usr/src/app/front
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

ENV ESCRIPTORIUM_SRC=/escriptorium-src
COPY --from=frontend ${ESCRIPTORIUM_SRC} ${ESCRIPTORIUM_SRC}

# set work directory
WORKDIR /usr/src/app

RUN cp ${ESCRIPTORIUM_SRC}/app/entrypoint.sh /usr/src/app/entrypoint.sh && \
    cp ${ESCRIPTORIUM_SRC}/app/manage.py /usr/src/app/manage.py && \
    cp ${ESCRIPTORIUM_SRC}/app/requirements.txt /usr/src/app/requirements.txt && \
    cp ${ESCRIPTORIUM_SRC}/app/uwsgi.ini /usr/src/app/uwsgi.ini && \
    cp -r ${ESCRIPTORIUM_SRC}/app/apps /usr/src/app/apps && \
    cp -r ${ESCRIPTORIUM_SRC}/app/escriptorium /usr/src/app/escriptorium && \
    cp -r ${ESCRIPTORIUM_SRC}/app/locale /usr/src/app/locale && \
    cp -r ${ESCRIPTORIUM_SRC}/app/homepage /usr/src/app/homepage && \
    rm -rf ${ESCRIPTORIUM_SRC}
COPY --from=frontend /build/dist /usr/src/app/front

WORKDIR /usr/src/app

COPY ./escriptorium/local_settings.py /usr/src/app/escriptorium/local_settings.py
RUN chmod 644 /usr/src/app/escriptorium/local_settings.py

# We want to replicate PU CDH's Ansible tasks for eScriptorium:
#
#   https://github.com/Princeton-CDH/cdh-ansible/blob/013fd75dfa9c857d025b97b02c95e2072166264a/roles/escriptorium_setup/tasks/main.yml
#
# They ensure eScriptorium will use the htr2hpc module for model and segmentation training. Specifically, they:
#
# 1. rename the train and segtrain functions in tasks.py to es_train and es_segtrain
# 2. import segtrain and train functions from htr2hpc.tasks

# rename the train and segtrain functions in tasks.py
ENV TASKS_FILE=/usr/src/app/apps/core/tasks.py
RUN sed -E -i 's/^( *)def segtrain/\1def es_segtrain/' ${TASKS_FILE}
RUN sed -E -i 's/^( *)def train/\1def es_train/' ${TASKS_FILE}

# Import the functions htr2hpc.tasks module just above "@shared_task...\ndef es_segtrain..."
RUN line_number=$(($(grep -n "^ *def es_segtrain" ${TASKS_FILE} | cut -d: -f1) - 1)) && \
    echo "${line_number}" | grep -q "^[0-9][0-9]*$" && \
    sed -i "${line_number}i from htr2hpc.tasks import segtrain, train" ${TASKS_FILE} && \
    sed -i "${line_number}i # EDITED BY pennlib-escritorium Dockerfile" ${TASKS_FILE}

#     - name: Expose read-write training accuracy model field in API
# see: the ansible task referenced above
ENV SERIALIZERS_PY=/usr/src/app/apps/api/serializers.py
RUN sed -E -i "s/'accuracy_percent', 'rights',/'accuracy_percent', 'training_accuracy', 'rights',/" ${SERIALIZERS_PY}

# Add htr2hpc to requirements.txt and run `pip install`
# for local development just add this project as ./
RUN mkdir /htr2hpc
COPY src/ /htr2hpc/src/
RUN ls /htr2hpc/
COPY pyproject.toml /htr2hpc/
COPY README.md /htr2hpc/
RUN echo  >> requirements.txt
RUN echo '/htr2hpc/' >> requirements.txt
RUN pip --no-cache-dir install --root-user-action ignore -r requirements.txt

# Change the django port; configure processes
COPY ./escriptorium/uwsgi.ini /usr/src/app/
RUN chmod 644 /usr/src/app/uwsgi.ini

# update entry point to set the site based on ESCRIPTORIUM_HOST
COPY ./escriptorium/entrypoint.sh /usr/src/app/
RUN chmod 755 /usr/src/app/entrypoint.sh

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
