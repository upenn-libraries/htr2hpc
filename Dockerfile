FROM registry.gitlab.com/scripta/escriptorium:dev-new-ui-alpha-rev8

WORKDIR /usr/src/app

COPY ./escriptorium/local_settings.py /usr/src/app/escriptorium/local_settings.py

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
#      ansible.builtin.replace:
#        path: "{{ install_root }}/app/apps/api/serializers.py"
#        # accuracy_percent only occurs once in this file, in the list of
#        # fields for OCRModelSerializer.
#        # Add training accuracy immediately after.
#        regexp: "\\'accuracy_percent\\', \\'rights\\',"
#        replace: "'accuracy_percent', 'training_accuracy', 'rights',"
ENV SERIALIZERS_PY=/usr/src/app/apps/api/serializers.py
RUN sed -E -i "s/'accuracy_percent', 'rights',/'accuracy_percent', 'training_accuracy', 'rights',/" ${SERIALIZERS_PY}

# Add htr2hpc to requirements.txt and run `pip install`
RUN cp requirements.txt requirements.txt.bak
COPY ./escriptorium/extra_requirements.txt /usr/src/app/extra_requirements.txt
RUN cat requirements.txt.bak extra_requirements.txt | sort | uniq > requirements.txt
RUN rm requirements.txt.bak extra_requirements.txt
RUN pip --no-cache-dir install --root-user-action ignore -r requirements.txt

# update entry point to set the site based on ESCRIPTORIUM_HOST
COPY ./escriptorium/entrypoint.sh /usr/src/app/
RUN chmod 755 /usr/src/app/entrypoint.sh

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
