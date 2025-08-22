# htr2hpc docker

Penn Libraries' htr2hpc provides Dockerfile and docker-compose files for development and portainer deployments of eScriptorium with htr2hpc.

The Dockerfile and docker compose configurations automate the installation steps in the [README](README.md) and [Princeton CDH's Ansible playbook](https://github.com/Princeton-CDH/cdh-ansible/blob/main/playbooks/escriptorium.yml).

This file provides instructions for docker deployment in development and on portainer.

## GPC installation for development and portainer deployment

HTR2HPC is both a django application that integrates with eScriptorium and a command-line application `htr2hpc-train` that is run on the HPC cluster. Both pieces must be installed and operating. For instructions on installing `htr2hpc-train` on the GPC see the [training README](src/htr2hpc/train/README.md). 

## Development deployment

Copy `variables.env_example` to `variables.env` and edit it to match your environment. See "Configuration variables" for more information.

```bash
cp  variables.env_example variables.env
```

Create an SSH key.

```bash
$ mkdir ssh
$ ssh-keygen -N "" -f ./ssh/htr2hpc_ed25519 -t ed25519
$ ls ssh
htr2hpc_ed25519     htr2hpc_ed25519.pub
```

Add the `./ssh/htr2hpc_id_rsa.pub` public key to the `${HOME}/.ssh/authorized_keys` file on the HPC cluster. See "SSH key authentication" below for more information.

Then build and run:

```bash
docker compose build --no-cache
docker compose up
# or, if you don't want to see the logs:
# docker compose up -d
```

eScriptorium should be available at http://localhost:8080. Use the admin username and password from `variables.env`.

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

Or, more thorough:

```bash
docker compose down -v --remove-orphans && docker container prune -f && { [[ -n "$(docker volume ls -q -f name=htr2hpc)" ]] && docker volume rm -f $(docker volume ls -q -f name=htr2hpc) || docker compose build --no-cache && docker compose up; }
```

### Configuration variables

For model training in development you'll need to edit the variables: `ESCRIPTORIUM_HOST`, `HPC_SSH_USER`, and `HPC_WORKING_DIR`. `ESCRIPTORIUM_HOST` should be set to the protocol, local machine public IP, and nginx port; e.g., http://1.2.3.4:8080.

NOTE: I haven't been able to get training to work from my laptop. (de 2025-08-22)

```shell
ESCRIPTORIUM_HOST=example.com  # The host escriptorium is running on
HPC_HOSTNAME=hpc.host.edu      # The hostname of the HPC cluster
HPC_SSH_USER=uername           # Username if one account is used for training
```

### SSH key authentication

htr2hpc relies on ssh secure authentication to run slurm jobs on the HCP cluster. By default, the key is expected at `./ssh/htr2hpc_ed25519`.

The development docker compose file maps local `./ssh` to `/usr/src/app/.ssh` in the docker container.

```
# docker-compose.yml
x-app:
  # ...
  volumes:
    - ./ssh:/usr/src/app/.ssh
```

_**IMPORTANT: Do not check the ssh key into version control!**_

The directory `./ssh` is in the `.gitignore` file and, thus, will ignored by git commands. If you put the ssh key in another directory in this project, make sure it is not checked into version control.

## What this repository does

This repo provides a docker deployment that builds a custom instance of eScriptorium with the Penn Libraries fork of htr2hpc and runs it in a docker compose environment.

The deployment is based on the htr2hpc installation instructions and the Princeton-CDH Ansible deployment scripts, https://github.com/Princeton-CDH/cdh-ansible/

Useful links:

- [eScriptorium playbook](https://github.com/Princeton-CDH/cdh-ansible/blob/main/playbooks/escriptorium.yml)
- [Staging variables](https://github.com/Princeton-CDH/cdh-ansible/blob/main/inventory/group_vars/htr_staging/vars.yml)
- [escriptorium_setup tasks](https://github.com/Princeton-CDH/cdh-ansible/blob/main/roles/escriptorium_setup/tasks/main.yml)

The `docker-compose.yml` file is adapted from the official eScriptorium repository (https://gitlab.com/scripta/escriptorium). It changes the service configurations for the `app` and `nginx` services to use locally built images, `pennlib-escriptorium` and `pennlib-escriptorium-nginx`, respectively.

The `pennlib-escriptorium` image is built from `./Dockerfile`. It pulls the latest eScriptorium image, then

- adds the `escriptorium/local_settings.py` file, which imports the htr2hpc module
- modifies the `requirements.txt` file to include the htr2hpc module, 
- add the `escriptorium/uwsgi.ini` custom web server configuration, and
- runs `pip install` to install the htr2hpc module.

The `pennlib-escriptorium-nginx` image is built from `./nginx/Dockerfile`. It replaces the original nginx image, `registry.gitlab.com/scripta/escriptorium/nginx:latest`, which is two years old and does not include the eScriptorium proxy configuration.

**TODO**: The docker-compose.yml file still refers to `registry.gitlab.com/scripta/escriptorium/mail`, which, like the nginx image, is two years old. It may need to be replaced as well.

## Portainer

Use `Dockerfile.portainer`, `nginx/Dockerfile`, `docker-compose.portainer.yml`, and `variables.env.portainer_example` for Portainer deployments.

The steps for deployment are these:

1. Build the htr2hpc image
2. Build the htr2hpc-nginx image
3. Create the stack using `docker-compose.portainer.yml` and edited `variables.portainer`

**(1) Build the HTR2HPC image**

Build htr2hpc image on portainer using `Dockerfile.portainer`. 

On the Images > Build Image page:

   - Name the image `htr2hpc`
   - Paste the content of `Dockerfile.portainer` into the Web Editor
   - Upload the files from `./escriptorium`: `entrypoint.sh, extra_requirements.txt, local_settings.py, uwsgi.ini`
   - Build the image

**(2) Build the HTR2HPC Nginx image**

On the Images > Build Image page:

- Name the image `htr2hpc-nginx`
- Paste the content of `nginx/Dockerfile` into the Web Editor
- Upload the file `nginx.conf` from `./nginx`
- Build the image

**(3) Create the stack**

On the 'Stacks > Add stack' page

- Name the stack: `htr2hpc`
- Paste the content of `docker-compose.portainer.yml` in the web editor box
- Click on 'Advanced mode' under Environments variables and paste in the content `variables.portainer`
- Edit the environment variables 
- Click 'Deploy the stack' 

If this is the initial setup, the private SSH key file should be added to the volume `ssh`. This can be done by bashing into the web container and creating a private key file in `/usr/src/app/.ssh`. In the default configuration this is an ed25519 key named `htr2hpc_ed25519` 

### Trobleshooting

#### Bad gateway

Bad gateway errors can arise for a couple of reasons.

1. The web (django) container has not completely started. Check the log for web container and look for the notice that the wsgi workers have been spawned

   - ```*** uWSGI is running in multiple interpreter mode ***
      spawned uWSGI master process (pid: 1)
      spawned uWSGI worker 1 (pid: 75, cores: 1)
      spawned uWSGI worker 2 (pid: 76, cores: 1)
      spawned uWSGI worker 3 (pid: 77, cores: 1)
      spawned uWSGI worker 4 (pid: 78, cores: 1)
      spawned uWSGI http 1 (pid: 79)
      ```
2. The web container has been redeployed and assigned an IP not known to the nginx server. Try restarting nginx.
