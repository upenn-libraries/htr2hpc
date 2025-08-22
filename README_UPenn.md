# HTR2HPC Notes

HTR2HPC (htr2hpc) has three components:

- A replacement for eScriptorium's login that uses Princeton's authentication
- Training components:
  - Tasks that replace the eScriptorium celery tasks so that training jobs are sent to the GPC
  - A Python script that runs on the GPC (see `src/htr2hpc/train/README.md`) that constructs the Ketos training command and communicates with eScriptorium

We are not using the first of these, the login replacement. Instead, we'll use local accounts.

## Changes to htr2hpc

Changes have been made to adapt htr2hpc-train for Penn SAS's HPC GPC2 cluster and to dockerize the htr2hpc eScriptorium instance.

### htr2hpc-train changes

- GitHub URLs are changed to point to the Penn repository for HTR2HPC:
  - https://github.com/upenn-libraries/htr2hpc.git
- The Slurm module load names have been changed from `anaconda3` to `miniforge3`
- The `htr2hpc-train` simple_slurm.Slurm job constructor has been modified to specify `--qos` and `--partition`
- Remote GPC working directory has been added as a setting `settings.HPC_WORKING_DIR`, and defaults to `${HOME}/htr2hpc`. HTR2HPC uses `/scratch` for its working directory; e.g., `working_dir = f"/scratch/gpfs/{user.username}/htr2hpc"`. (See notes below on scratch.)
- HTR2HPC connects to the GPC using the username of the currently logged-in user. The Penn instance will have all users connection to a single account on the HPC cluster. A variable `settings.HPC_SSH_USER` has been added to hold this account name.
- The remote command in `htr2hpc.tasks.start_remote_training()` has been changed to invoke a bash login shell so that Slurm environment tools are available. It's been changed:
  - from  `f"module load anaconda3/2024.6 && conda run -n htr2hpc {train_cmd}" `
  - to ` f'bash -l -c "module load miniforge3/24.11.3 && conda run -n htr2hpc {train_cmd}"'`
- An 'htr2hpc-train' option `--log-level` has been added.
- `htr2hpc.train.slurm.slurm_job_stats()` uses the `jobstats` program to get after-job stats for training jobs. `jobstats` is not available on the SAS GPC. The function has been changed to use the slurm `sacct` application instead.

### Docker changes

HTR2HPC has been dockerized for development and production portainer deployment. The following files have beend added for docker support:

- Dockerfile
- Dockerfile.portainer
- README_Docker.md
- docker-compose.override.yml_example
- docker-compose.portainer.yml
- docker-compose.yml
- escriptorium/
  - entrypoint.sh
  - extra_requirements.txt
  - local_settings.py
  - uwsgi.ini
- nginx/
  - Dockerfile
  - nginx.conf
- variables.env.portainer_example
- variables.env_example

There are Dockerfiles to build development and portainer htr2hpc eScriptorium images and an nginx image.

## HPC Filesystem Configuration Comparison

Penn SAS's GPC2 and della (the HPC cluster used by PU CDH) have significantly different filesystem behaviors that affect how htr2hpc operates.

### Filesystem Access Patterns

#### Della Configuration
- **`/home`**: Accessible only to the head node; **not accessible** to compute nodes running Slurm jobs
- **`/scratch`**: Persistent storage accessible from any node

#### SAS GPC2 Configuration  
- **`/home`**: Accessible from all nodes (head and compute)
- **`/scratch`**: 
  - Accessible **only** from compute nodes during Slurm jobs
  - Each compute node has its own isolated `/scratch` filesystem

### Compatibility Issues with htr2hpc

The SAS GPC2 scratch configuration is incompatible with htr2hpc's default behavior. Here's why:

#### Default htr2hpc Workflow
1. `htr2hpc-train` runs on the head node and stages training files in `/scratch/gpfs/{user.username}/htr2hpc`
2. Slurm training jobs use this same directory as their working directory
3. Each training session consists of two Slurm jobs sharing the same working directory

#### Problems on SAS GPC2
1. **Head node access limitation**: `htr2hpc-train` cannot access `/scratch` from the head node for file staging and cleanup operations

2. **Node isolation**: Each compute node has its own `/scratch` filesystem. Since Slurm assigns compute nodes at runtime, the two jobs in a training session may be assigned to different nodes and lose access to shared files

### Solution
To address these filesystem limitations, we use `$HOME/htr2hpc` exclusively for running Slurm jobs on SAS GPC2, leveraging the fact that `/home` is accessible from all nodes in this environment.

## Tasks

The HTR2HPC deploy process rewrites the eScriptorium celery `tasks.py` file so that:

1. The functions `segtrain(...)` and `train(...)` are renamed `es_segtrain(...)` and `es_train(...)`
2. The HTR2HPC tasks `segtrain` and `train` are imported before the renamed functions so that eScriptorium calls the HTR2HPC training functions instead of its own tasks

> **Question:** Why not just import the functions at the end of the file? That should replace the `segtrain` and `train` functions with the HTR2HPC ones. The reason may have to do with the order of imports.

The `segtrain` and `train` methods construct the command that is sent to the `htr2hpc-train` script on the remote GPC.

## Training: `htr2hpc.train`, `src/htr2hpc/train`

The `htr2hpc-train` script constructs, runs, and monitors the Ketos training commands that are run on the GPC (see `src/htr2hpc/train/run.py`, `src/htr2hpc/train/slurm.py`). It also communicates status with and sends updates to eScriptorium via a custom API (see `src/htr2hpc/api_client.py`). The API:

- Manages changes to application models (i.e., Document, ML Model, Task)
- Requests document information (document list and document details, lists of images, etc.)
- Downloads files (models, ground truth, images)
- Updates eScriptorium with task status information

The `htr2hpc.train.run.main()` function defines the parameters and options of the `htr2hpc-train` command. The work itself is handled by the `htr2hpc.train.run.TrainingManager` class. Its `segmentation_training` and `recognition_training` methods call the `htr2hpc.train.slurm` `segtrain` and `recognition_train` functions. The setup and configure the Slurm jobs and build the Ketos training commands. See below for more on HPC GPC and Slurm.

## Training Workflow Details

### eScriptorium Training Workflow

The `htr2hpc.tasks` module provides `segtrain()` and `train()` functions for segmentation and recognition training. These methods construct the `htr2hpc.train` command, with:

- Subcommand: `transcription` or `segmentation`
- The command options, including the Document, TaskReport, and Model IDs
- The output directory

The training method then invokes `start_remote_training()`:

```python
success = start_remote_training(
    user, working_dir, cmd, document_pk, model.pk, task_report
)
```

Specifically `start_remote_training()`:

- Establishes the SSH connection with the GPC, logging in as the eScriptorium user (see the Changes section above)
- Changes to the `working_dir`
- Sets the `ESCRIPTORIUM_API_TOKEN` environment variable used by `htr2hpc-train` to communicate with eScriptorium
- Loads the `conda` module (`miniforge3` for UPenn) and activates the `htr2hpc` environment
- Runs the `htr2hpc-train` command

### `htr2hpc-train` Training Workflow

#### `htr2hpc.train.run`

The work of `htr2hpc-train` is done in the `htr2hpc.train.run` module. Its main method parses the command line arguments, creates an `htr2hpc.train.TrainingManager` instance (`training_mgr`), and calls `training_mgr.training_prep`, which retrieves the training data from eScriptorium (images, model, etc.). It then runs either `training_mgr.segmentation_training()` or `training_mgr.recognition_training()`, based on the CLI subcommand.

The training methods assemble Slurm job parameters, paths, and resource estimates and call `htr2hpc.train.slurm.segtrain()` or `htr2hpc.train.slurm.recognition_train()`, which returns the Slurm job ID.

When the job has started `training_mgr` calls `self.monitor_slurm_job(job_id)`.

`monitor_slurm_job()` communicates job status information to eScriptorium via the `htr2hpc.api_client.eScriptoriumAPIClient` instance. It relies on `htr2hpc.train.slurm` functions that query job queue status, job status, and job stats.

The usage for `htr2hpc-train` is:

```shell
usage: htr2hpc-train [-h] -d DOCUMENT_ID [-m MODEL_ID] [-u | --update-if-improved] [--model-name MODEL_NAME] [-p PARTS] [-tr TASK_REPORT_ID] [--existing-data] [--clean | --no-clean]
                     [--progress | --no-progress] [-w NUM_WORKERS] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                     {segmentation,transcription} ... BASE_URL WORKING_DIR

Export content from eScriptorium and train or fine-tune models

positional arguments:
  BASE_URL              Base URL for eScriptorium instance (without /api/)
  WORKING_DIR           Working directory where data should be downloaded (must NOT already exist)

options:
  -h, --help            show this help message and exit
  -d DOCUMENT_ID, --document DOCUMENT_ID
                        Document id to export
  -m MODEL_ID, --model MODEL_ID
                        Optional model id to use for fine-tuning
  -u, --update          Update the specified model with the best model from training (requires --model)
  --update-if-improved  Update the specified model with the best model from training ONLY if improved on original
  --model-name MODEL_NAME
                        Name to be used for newly trained model (not compatible with --update)
  -p PARTS, --parts PARTS
                        Optional list of part ids for training. Format as #,#,# or #-##.(if not specified, uses entire document)
  -tr TASK_REPORT_ID, --task-report TASK_REPORT_ID
                        Optional task report id, for reporting sbatch and slurm output
  --existing-data       Use existing data from a previous run
  --clean, --no-clean   Clean up temporary working files after training ends
  --progress, --no-progress
                        Show progress
  -w NUM_WORKERS, --workers NUM_WORKERS
                        Number of workers for training task (default: 8)
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

mode:
  supported training modes

  {segmentation,transcription}
```

#### `htr2hpc.train.slurm`

`htr2hpc.train.slurm` uses the `simple_slurm` python module (https://github.com/amq92/simple_slurm). The functions `segtrain()` and `recognition_train()` set up and enqueue the Slurm batch job. Setup includes the Slurm job parameters (nodes, cpus_per_task, GPU spec, etc.; see below for details), commands to load the HTR2HPC environment, and the full `ketos` command.

`segtrain()` and `recognition_train()` queue the Slurm batch and return the job ID:

```python
return segtrain_slurm.sbatch(segtrain_cmd)
```

### Slurm Job Parameters

Slurm parameters are passed to the `simple_slurm.Slurm` constructor. Here is Princeton's `recognition_slurm` instantiation:

```python
recogtrain_slurm = Slurm(
    nodes=1,
    ntasks=1,
    cpus_per_task=num_workers,
    mem_per_cpu=mem_per_cpu,
    gres=["gpu:1"],
    job_name=f"{prelim_opt}train:{output_model.name}",
    output=f"train_{Slurm.JOB_ARRAY_MASTER_ID}.out",
    time=training_time,
)
```

These parameters correspond to, in order:

```
-N, --nodes=N               number of nodes on which to run (N = min[-max])
-n, --ntasks=ntasks         number of tasks to run
-c, --cpus-per-task=ncpus   number of cpus required per task
    --mem-per-cpu=MB        maximum amount of real memory per allocated
                            cpu required by the job
    --gres=list             required generic resources (see below)
-J, --job-name=jobname      name of job
-o, --output=out            file for batch script's standard output
-t, --time=minutes          time limit
```

**--gres**: This is where GPUs are specified (see https://slurm.schedmd.com/gres.html).

UPenn SAS HPC requires specifying partition and quality of service (see HPC GPC2 and Slurm below for details). The Slurm CLI parameters are:

```
-q, --qos=qos               quality of service
-p, --partition=partition   partition requested
```

~~For SAS's GPC we should use `--qos=low --partition=low`.~~

We need to use the `low` quality of service value, and a partition that provides GPU access; not all GPC partitions do.
For SAS's GPC we should use `--qos=low --partition=low_gpu_a40`?


## Slurm QOS and partitions

**Quality of Service:** From the Slurm documentation (https://slurm.schedmd.com/qos.html), quality of service:

> will affect the job in three key ways: scheduling priority, preemption, and resource limits.

**Partition:** A Slurm cluster consists of nodes grouped under partitions. From the Slurm Quick Start guide (https://slurm.schedmd.com/quickstart.html):

> The partitions can be considered job queues, each of which has an assortment of constraints such as job size limit, job time limit, users permitted to use it, etc.

The `sinfo` command shows summary information about cluster partitions and nodes. The `squeue` command shows detailed information about jobs, the partitions and nodes they are running on.

## HPC GPC2 and Slurm

SAS HPC provides examples and links to Slurm documentation here:

- https://computing.sas.upenn.edu/gpc
- https://computing.sas.upenn.edu/gpc/software-environments
- https://computing.sas.upenn.edu/gpc/job/slurm

They also provide useful links to Slurm documentation:

- https://slurm.schedmd.com/quickstart.html (quickstart guide)
- https://slurm.schedmd.com/pdfs/summary.pdf (list of Slurm command options)
- https://slurm.schedmd.com/man_index.html (man pages for Slurm)

The sign-up email from HPC provides these additional notes:

> Please do not run jobs on the head node; use
>
```bash
srun -p low --qos=low --pty bash
```
>
> for a preemptable interactive session on a compute node,
>
```bash
srun -p gpc2_compute --qos=normal --pty bash
```
>
> for a non-preemptable interactive session on a compute node, or schedule jobs via the queue.
>
> We have sample scripts for our older cluster, GPC, here: https://computing.sas.upenn.edu/gpc/job/slurm - you can add these GPC2 partition names and qos for GPC2 job wrapper scripts:
>
```bash
#SBATCH -p gpc2_compute
#SBATCH --qos=normal
```
>
> or
>
```bash
#SBATCH -p low
#SBATCH --qos=low
```