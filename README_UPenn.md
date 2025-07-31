# htr2hpc notes

H2H (htr2hpc) has three components:

– A replacement for eScriptorium's login that uses Princeton's authentication
– Training components:
    – Tasks that replace the eScriptorium celery tasks so that training jobs are sent to the GPC
    – A python script that runs on the GPC (see src/htr2hpc/train/README.md) that constructs the keto training command and communicates with eScriptorium

We are not using the first of these, the login replacement. Instead, we'll use local accounts.

## Tasks

The h2h deploy process rewrites the eScriptorium celery tasks.py file so that: 

1. The functions `segtrain(...)` and `train(...)` are renamed `es_segtrain(...)` and `es_train(...)` 
2. The h2h tasks segtrain and train are imported before the renamed functions so that eScriptorium calls the h2h training functions instead of its own tasks. 

> Question: Why not just import the functions at the end of the file? That should replace the segtrain and train functions with the h2h ones.

The segtrain and train methods construct the command that is sent to the htr2hpc-train script on the remote GPC.

## Training: `htr2hpc.train`, `src/htr2hpc/train`

The htr2hpc-train command constructs the keto training command that is run on the GPC (`src/htr2hpc/train/run.py`, `src/htr2hpc/train/slurm.py`). It also communicates with eScriptorium via an API class (see `src/htr2hpc/api_client.py`). The API manages changes to models, requesting document information (document list and document details, lists of images, etc.), downloading files (models, ground truth, images), and updating eScriptorium with task status information.

The `htr2hpc.train.run.main()` function defines the parameters and options of the htr2hpc-train command. The work itself is handled by the `hhtr2hpcpc.train.run.TrainingManager` class. Its `segmentation_training` and `recognition_training` methods call the `htr2hpc.train.slurm` `segtrain` and `recognition_train` functions, which construct the slurm jobs with the commands needed set up the slurm environment and construct the keto training command.

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

The htr2hpc-train slurm job constructor will need to be modified to specify `--qos` and `--partion`.

