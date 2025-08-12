# htr2hpc docker

Penn Libraries' htr2hpc a Dockerfile and development docker-compose.yml for an eScriptorium instance with htr2hpc.

The Dockerfile and docker compose configuration automate the installation steps in the [README](README.md) and [Princeton CDH's Ansible playbook](https://github.com/Princeton-CDH/cdh-ansible/blob/main/playbooks/escriptorium.yml).

## Quickstart

Copy `variables.env_example` to `variables.env` and edit it to match your environment. See "Configuration variables" for more information.

```bash
cp  variables.env_example variables.env
```

Create an SSH key and add the public key to the `${HOME}/.ssh/authorized_keys` file on the HPC cluster. See

```bash
$ mkdir ssh
$ ssh-keygen -N "" -f ./ssh/htr2hpc_id_rsa -t rsa -b 4096
$ ls ssh
htr2hpc_id_rsa     htr2hpc_id_rsa.pub
```

Add the `./ssh/htr2hpc_id_rsa.pub` public key to the `${HOME}/.ssh/authorized_keys` file on the HPC cluster. See "SSH key authentication" below for more information.

Then build and run:

```bash
docker compose build --no-cache
docker compose up
# or, if you don't want to see the logs:
# docker compose up -d
```

eScriptorium should be available at http://localhost:8080. Use the admin
username and password from `variables.env`.

### To clear everything out and start over:

```bash
docker compose down
docker volume rm $(docker volume ls -q -f name=htr2hpc)
docker compose build --no-cache
docker compose up
```

Or, if you prefer one line:

```bash
docker compose down && docker volume rm $(docker volume ls -q -f name=htr2hpc) && docker compose build --no-cache && docker compose up
```

## Configuration variables

For development, most of the variables can be left as is. You will want to change the following to match your environment:

```shell
ESCRIPTORIUM_HOST=example.com  # The host escriptorium is running on
HPC_HOSTNAME=hpc.host.edu      # The hostname of the HPC cluster
```

## SSH key authentication

htr2hpc relies on ssh secure authentication to run slurm jobs on the HCP cluster.

The docker compose dev deployment uses docker secrets to store the ssh key on the server. The key is expected to be at `./ssh/htr2hpc_id_rsa`:

```
# docker-compose.yml
secrets:
  ssh_key:
    file: ./ssh/htr2hpc_id_rsa
```

_**IMPORTANT: Do not check the ssh key into version control!**_

The directory `./ssh` is in the `.gitignore` file and, thus, will ignored by git commands. If you put the ssh key in another directory in this project, make sure it is not checked into version control.

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
