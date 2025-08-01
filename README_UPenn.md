# htr2hpc notes

H2H (htr2hpc) has three components:

- A replacement for eScriptorium's login that uses Princeton's authentication

- Training components:
    - Tasks that replace the eScriptorium celery tasks so that training jobs are sent to the GPC
    - A python script that runs on the GPC (see src/htr2hpc/train/README.md) that constructs the keto training command and communicates with eScriptorium

We are not using the first of these, the login replacement. Instead, we'll use local accounts.

## Tasks

The h2h deploy process rewrites the eScriptorium celery `tasks.py` file so that: 

1. The functions `segtrain(...)` and `train(...)` are renamed `es_segtrain(...)` and `es_train(...)` 
2. The h2h tasks segtrain and train are imported before the renamed functions so that eScriptorium calls the h2h training functions instead of its own tasks. 

> Question: Why not just import the functions at the end of the file? That should replace the segtrain and train functions with the h2h ones. The reason may have to with the order of imports.

The segtrain and train methods construct the command that is sent to the htr2hpc-train script on the remote GPC.

## Training: `htr2hpc.train`, `src/htr2hpc/train`

The `htr2hpc-train` script constructs the ketos training command that is run on the GPC (`src/htr2hpc/train/run.py`, `src/htr2hpc/train/slurm.py`). It also communicates with eScriptorium via an API class (see `src/htr2hpc/api_client.py`). The API:

- manages changes to application models (i.e., Document, ML Model, Task); requests document information (document list and document details, lists of images, etc.); 
- downloads files (models, ground truth, images); and 
- updates eScriptorium with task status information.

The `htr2hpc.train.run.main()` function defines the parameters and options of the htr2hpc-train command. The work itself is handled by the `hhtr2hpcpc.train.run.TrainingManager` class. Its `segmentation_training` and `recognition_training` methods call the `htr2hpc.train.slurm` `segtrain` and `recognition_train` functions, which construct the slurm jobs with the commands needed set up the slurm environment and construct the keto training command. See below for more on HPC GPC and Slurm.

## Training workflow details

### eScriptorium training workflow

The `htr2hp.tasks` module provides `segtrain()`and `train()` functions for segmentation and recognition training. These methods construct the `htr2hpc.train` command, with:

- subcommand, `transcription` or `segmentation`; 
- the command options, including the Document, TaskReport and Model IDs; and 
- the output directory. 

The training method then invokes `start_remote_training()`:

```python
success = start_remote_training(
    user, working_dir, cmd, document_pk, model.pk, task_report
)
```

`start_remote_training()`:

- establishes the SSH connection with the GPC, logging in as the eScriptorium user (see the Changes section below); 
- cd's to the `working_dir`, loads the `conda` module (`miniforge3` for UPenn); 
- runs the `htr2hpc-train` command; and
- sets the `ESCRIPTORIUM_API_TOKEN` environment variable used by `htr2hpc-train` to communicate with eScriptorium.

### `htr2hpc-train` training workflow

The work of `htr2hpc-train` is done in the `htr2hpc.train.run` module. Its main method parses the command line arguments, creates a `htr2hpc.train.TrainingManager` instance, `training_mgr`, and calls `training_mgr.training_prep` to retrieve training data (images, model, etc.). It then runs either `training_mgr.segmentation_training()` or `training_mgr.recognition_training()`, based on the CLI subcommand. 

The training methods assemble slurm job parameters, paths, and resource estimates. The training function calls `htr2hpc.train.slurm.segtrain()` or `htr2hpc.train.slurm.recognition_train()`, which returns the Slurm job ID; and then `self.monitor_slurm_job(job_id)`.

`monitor_slurm_job()` communicates job status information to eScriptorium via the `htr2hpc.api_client.eScriptoriumAPIClient` instance. It relies on `htr2hpc.training.slurm` functions that query job queue status, job status, and job stats.

`htr2hpc.training.slurm` uses the `simple_slurm` module (https://github.com/amq92/simple_slurm). The functions `segtrain()` and `recognition_train()` construct and enqueue the slurm batch job. Setup includes the Slurm job parameters (nodes, cpus_per_task, GPU spec, etc.; see below for details); commands to the load the htr2hpc environment; and the `ketos` command.  The training functions queue the slurm batch and return the job ID:

```python
return segtrain_slurm.sbatch(segtrain_cmd)
```


### Slurm job parameters

Slurm parameters a passed to the `simple_slurm.Slurm` contructor. Here is Princeton's recognition_slurm instantiation:

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
    partition="low",
    qos="low",
)
```

These params correspond to, in order:

```
-N, --nodes=N               number of nodes on which to run (N = min[-max])
-n, --ntasks=ntasks         number of tasks to run
-c, --cpus-per-task=ncpus   number of cpus required per task
    --mem-per-cpu=MB        maximum amount of real memory per allocated
                            cpu required by the job.
    --gres=list             required generic resources (see below)
-J, --job-name=jobname      name of job
-o, --output=out            file for batch script's standard output
-t, --time=minutes          time limit
```

UPenn SAS HPC requires specifying partition and quality of service (see HPC GPC2 and Slurm below for details). The Slurm CLI params are:

```
-q, --qos=qos               quality of service
-p, --partition=partition   partition requested
```

Partition: A slurm cluster consists of nodes grouped under partitions. From the Slurm Quick Start guide (https://slurm.schedmd.com/quickstart.html):

> The partitions can be considered job queues, each of which has an assortment of constraints such as job size limit, job time limit, users permitted to use it, etc.

The `sinfo` command shows summary information about cluster partitions and nodes. The `squeue` command show detailed information about jobs, the partitions and nodes they are running on.

Quality of Service: From the Slurm documentation (https://slurm.schedmd.com/qos.html) quality of service:

> will affect the job in three key ways: scheduling priority, preemption, and resource limits.

## Changes to htr2hpc-train for SAS HPC GPC2

- GitHub URLs are changed to point to the Penn repository for htr2hpc:
  - https://github.com/upenn-libraries/htr2hpc.git
- The module load names have been changed from `anaconda3` to `miniforge3`.
- TODO: The htr2hpc-train slurm job constructor will need to be modified to specify `--qos` and `--partion`.
- H2H uses `/scratch` for its working directory; e.g., `working_dir = f"/scratch/gpfs/{user.username}/htr2hpc"`. As of yet scratch is not writeable on GPC2. It's present on the `low` partition compute nodes, but is not writable. The `/scratch` dir has not been checked on the `gpc2_compute` partition.
- H2H connects to the GPC using the username of the currently logged-in user. We're going to use a single account.

## HPC GPC2 and Slurm

SAS HPC provides examples and links to Slurm documentation here: 

- https://computing.sas.upenn.edu/gpc
- https://computing.sas.upenn.edu/gpc/software-environments
- https://computing.sas.upenn.edu/gpc/job/slurm

They also give useful links to Slurm documentation:

- https://slurm.schedmd.com/quickstart.html (quickstart guide)
- https://slurm.schedmd.com/pdfs/summary.pdf (list of slurm command options)
- https://slurm.schedmd.com/man_index.html (man pages for slurm)

The sign-up email from HPC provides these addition notes:

> Please do not run jobs on the head node; use 
> 
> srun -p low --qos=low --pty bash 
> 
> for a preemptable interactive session on a compute node, 
> 
>   `srun -p gpc2_compute --qos=normal --pty bash`
> 
> for a non-preemptable interactive session on a compute node, or schedule jobs via the queue.
> 
> We have sample scripts for our older cluster, GPC, here: https://computing.sas.upenn.edu/gpc/job/slurm - you can add these GPC2 partition names and qos for GPC2 job wrapper scripts:
> 
> ```
> #SBATCH -p gpc2_compute
> #SBATCH --qos=normal
> ``` 
> 
> or
> 
> ```
> #SBATCH -p low
> #SBATCH --qos=low
> ```

