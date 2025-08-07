# PennLib eScriptorium

PennLib eScriptorium is a dockerized version of eScriptorium that includes the Penn Libraries fork of the Princeton CDH htr2hpc module.

For more details see:

- [Princeton CDH htr2hpc](https://github.com/Princeton-CDH/htr2hpc)
- [UPenn fork of htr2hpc](https://github.com/upenn-libraries/htr2hpc)

## Quickstart

Copy `variables.env_example` to `variables.env` and edit it to match your environment.

```bash
cp  variables.env_example variables.env
```

The build and run:

```bash
docker compose build --no-cache
docker compose up
# or, if you don't want to see the logs:
# docker compose up -d
```

eScriptorium should be available at http://localhost:8080. Use the admin
username and password from `variables.env`.

WARNING: Do not attempt to train models. The htr2hpc module has not been updated
to work with Penn the SAS HPC GPC.

### To clear everything out and start over:

```bash
docker compose down
docker volume rm $(docker volume ls -q -f name=pennlib-escriptorium)
docker compose build --no-cache
docker compose up
```

Or, if you prefer one line:

```bash
docker compose down && docker volume rm $(docker volume ls -q -f name=pennlib-escriptorium) && docker compose build --no-cache && docker compose up
```

## What this repository does

This repo provides a docker deployment that builds a custom instance of
eScriptorium with the Penn Libraries fork of htr2hpc and runs it in a docker
compose environment.

The deployment is based on the htr2hpc installation instructions and the Princeton-CDH Ansible deployment scripts, https://github.com/Princeton-CDH/cdh-ansible/

Useful links:

- [eScriptorium playbook](https://github.com/Princeton-CDH/cdh-ansible/blob/main/playbooks/escriptorium.yml)
- [Staging variables](https://github.com/Princeton-CDH/cdh-ansible/blob/main/inventory/group_vars/htr_staging/vars.yml)
- [escriptorium_setup tasks](https://github.com/Princeton-CDH/cdh-ansible/blob/main/roles/escriptorium_setup/tasks/main.yml)

The `docker-compose.yml` file is adapted from the official eScriptorium
repository (https://gitlab.com/scripta/escriptorium). It changes the
service configurations for the `app` and `nginx` services to use locally
built images, `pennlib-escriptorium` and `pennlib-escriptorium-nginx`,
respectively.

The `pennlib-escriptorium` image is built from `./Dockerfile`. It pulls the
latest eScriptorium image, then

- adds the `escriptorium/local_settings.py` file, which imports the htr2hpc
  module
- modifies the `requirements.txt` file to include the htr2hpc module, and
- runs `pip install` to install the htr2hpc module.

The `pennlib-escriptorium-nginx` image is built from `./nginx/Dockerfile`.
It replaces the original nginx image,
`registry.gitlab.com/scripta/escriptorium/nginx:latest`, which is two years
old and does not include the eScriptorium proxy configuration.

**TODO**: The docker-compose.yml file still refers to `registry.gitlab.com/scripta/escriptorium/mail`, which, like the nginx image, is two years old. It may need to be replaced as well.

## TODO

Update htr2hpc in `escriptorium/extra_requirements.txt` to use a
yet-to-be-created fork of [htr2hpc](https://github.com/Princeton-CDH/htr2hpc).
The fork will remove the Princeton login configuration and modify the Slurm
jobs to work with Penn's HPC GPC.