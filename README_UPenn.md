# HTR2HPC for UPenn

HTR2HPC enables eScriptorium to leverage High Performance Computing (HPC) clusters for machine learning model training. This document covers the UPenn-specific implementation that adapts HTR2HPC for Penn SAS's GPC2 cluster.

## Overview

HTR2HPC consists of three main components:

1. **Authentication replacement** - Uses Princeton's authentication (not implemented in UPenn version)
2. **Training components** - Replace eScriptorium's Celery tasks to route training jobs to HPC
3. **HPC training script** - Python script that runs on the cluster to execute Ketos training

The UPenn implementation uses local accounts instead of the Princeton authentication system.

## Architecture

```
eScriptorium → HTR2HPC Tasks → SSH Connection → GPC2 Cluster
                    ↓                              ↓
              Task Management              htr2hpc-train script
                    ↓                              ↓
               Status Updates ← API Client ← Slurm Jobs (Ketos)
```

## Key Adaptations for UPenn GPC2

### Configuration Changes

| Component | Change | Reason |
|-----------|--------|---------|
| GitHub Repository | Updated to `upenn-libraries/htr2hpc` | Fork maintenance |
| Module Loading | Changed from `anaconda3` to `miniforge3/24.11.3` | GPC2 environment |
| Working Directory | Uses `${HOME}/htr2hpc` instead of `/scratch/gpfs/{user.username}/htr2hpc` | GPC2 filesystem limitations |
| SSH Authentication | Single shared HPC account via `HPC_SSH_USER` | Simplified user management |
| Slurm Parameters | Added `--qos` and `--partition` requirements | GPC2 cluster requirements |
| Job Statistics | Uses `sacct` instead of `jobstats` | Tool availability |

### Code Modifications

**Remote Command Execution**

`htr2hpc` runs the training jobs via SSH RPC. Because the default GPC2 SSH shell does not load the SLURM environment, we have to execute a bash login shell. 

```python
# Before
result = conn.run(
    f'module load anaconda3/2024.6 && conda run -n htr2hpc {train_cmd}',
    env={"ESCRIPTORIUM_API_TOKEN": api_token},
    warn=True,  # don't throw unexpected error on exit != 0
)


# After  
result = conn.run(
    f'bash -l -c "module load miniforge3/24.11.3 && conda run -n htr2hpc {train_cmd}"',
    env={"ESCRIPTORIUM_API_TOKEN": api_token},
    warn=True,  # don't throw unexpected error on exit != 0
)
```

**New Configuration Settings**
- `HPC_WORKING_DIR`: Remote working directory (default: `${HOME}/htr2hpc`)
- `HPC_SSH_USER`: Shared HPC account username
- `--log-level`: Added logging control to htr2hpc-train

## Filesystem Architecture

### Cluster Comparison

| Filesystem | Della (Princeton) | GPC2 (UPenn) |
|------------|-------------------|---------------|
| `/home` | Head node only | All nodes |
| `/scratch` | All nodes, persistent | Compute nodes only, per-node |

### Why We Use `/home` on GPC2

The default HTR2HPC workflow stages files in `/scratch`, but GPC2's configuration creates two critical issues:

1. **Head node isolation**: `htr2hpc-train` runs on the head node but cannot access `/scratch` for file staging
2. **Node-specific storage**: Each compute node has its own `/scratch`, so multi-job training sessions can't share files

**Solution**: Use `${HOME}/htr2hpc` as the working directory since `/home` is accessible from all nodes on GPC2.

## Docker Implementation

HTR2HPC has been containerized for both development and production deployment. 

### Added Files
```
Dockerfile                           # Development image
Dockerfile.portainer                 # Production image  
docker-compose.yml                   # Base composition
docker-compose.portainer.yml         # Production composition
docker-compose.override.yml_example  # Development overrides
README_Docker.md                     # Docker documentation
variables.env_example                # Environment template
variables.env.portainer_example      # Production environment template

escriptorium/
├── entrypoint.sh                    # Container startup script
├── extra_requirements.txt           # Additional Python packages
├── local_settings.py                # Django configuration
└── uwsgi.ini                        # WSGI server config

nginx/
├── Dockerfile                       # Nginx proxy image
└── nginx.conf                       # Reverse proxy configuration
```

See the [Docker README](README_Docker.md) for details.  

## Training Workflow

### eScriptorium Training Workflow

The `htr2hpc.tasks` functions `segtrain()` and `train()` replace the native eScriptorium tasks. The htr2hpc tasks run training tasks as slurm jobs on the HPC cluster via SSH RPC. They construct the command line `htr2hpc-train` commands and call `start_remote_training()`, which: 

- Establishes the SSH connection with the GPC
- Changes to the `working_dir`
- Sets the `ESCRIPTORIUM_API_TOKEN` environment variable used by `htr2hpc-train` to communicate with eScriptorium
- Loads the `conda` module (`miniforge3` for UPenn) and activates the `htr2hpc` environment
- Runs the `htr2hpc-train` command

### Remote Training Process

`htr2hpc-train` is installed on the HPC cluster. It constructs a Slurm batch job that runs the `ketos` command to perform that training.

**Command Line Interface**

```bash
htr2hpc-train [-h] -d DOCUMENT_ID [-m MODEL_ID] [-u | --update-if-improved] 
              [--model-name MODEL_NAME] [-p PARTS] [-tr TASK_REPORT_ID] 
              [--existing-data] [--clean | --no-clean] [--progress | --no-progress] 
              [-w NUM_WORKERS] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
              {segmentation,transcription} ... BASE_URL WORKING_DIR
```

#### Key `htr2hpc-train` Components

**TrainingManager Class** (`htr2hpc.train.run`)
- Parses command line arguments
- Retrieves training data from eScriptorium via API
- Coordinates segmentation or recognition training
- Monitors job status and communicates with eScriptorium

**Slurm Integration** (`htr2hpc.train.slurm`)
- Uses `simple_slurm` Python module for job management
- Configures job parameters (resources, queues, time limits)
- Submits jobs and returns job IDs for monitoring

#### Training Process
1. **Preparation**: Download images, models, and ground truth data
2. **Job Setup**: Configure Slurm parameters and Ketos commands  
3. **Execution**: Submit batch job to cluster
4. **Monitoring**: Track job status and report progress
5. **Completion**: Upload results and clean up temporary files

## Slurm Configuration

### Resource Specifications

**Recognition Training Example:**
```python
recogtrain_slurm = Slurm(
    nodes=1,                    # Single node
    ntasks=1,                   # One task
    cpus_per_task=num_workers,  # CPU cores per task
    mem_per_cpu=mem_per_cpu,    # Memory per CPU core
    gres=["gpu:1"],             # GPU requirement
    job_name=f"train:{model}",  # Job identification
    output="train.out",         # Output file
    time=training_time,         # Time limit
    qos="low",                  # Quality of service (UPenn)
    partition="low_gpu_a40"     # Partition with GPU access (UPenn)
)
```

### GPC2-Specific Requirements

**Quality of Service (QOS)**: Controls job scheduling priority and resource limits
- `low`: Preemptable jobs with lower priority
- `normal`: Standard priority, non-preemptable

**Partitions**: Different hardware configurations and access policies
- `low`: Preemptable compute nodes
- `low_gpu_a40`: GPU-enabled nodes (A40 cards)

### Interactive Sessions

For development and testing:

```bash
# Preemptable session
srun -p low --qos=low --pty bash

# Standard session  
srun -p gpc2_compute --qos=normal --pty bash
```

## API Communication

The `eScriptoriumAPIClient` handles communication between the HPC cluster and eScriptorium:

**Core Functions:**
- Download training data (images, models, ground truth)
- Update training task status
- Upload completed models
- Report job progress and statistics

**Authentication**: Uses `ESCRIPTORIUM_API_TOKEN` environment variable set by the SSH session

## Monitoring and Logging

**Job Status Tracking:**
- Real-time status updates via Slurm commands (`squeue`, `sacct`)
- Progress reporting to eScriptorium task system
- Configurable log levels for debugging

**Resource Monitoring:**
- Post-job statistics via `sacct` command
- CPU, memory, and GPU utilization tracking
- Training performance metrics

## Installation and Setup

See `README_Docker.md` for containerized deployment instructions.

### Environment Variables

Key settings for UPenn deployment:
```bash
HPC_SSH_USER=shared_hpc_account
HPC_WORKING_DIR=${HOME}/htr2hpc
ESCRIPTORIUM_API_TOKEN=your_token_here
```

## Troubleshooting

**Debug Mode:**
Use `htr2hpc-train` options `--log-level DEBUG` for detailed execution logging.

## References

**Slurm Documentation:**
- [Quick Start Guide](https://slurm.schedmd.com/quickstart.html)
- [Command Summary](https://slurm.schedmd.com/pdfs/summary.pdf)
- [Manual Pages](https://slurm.schedmd.com/man_index.html)

**UPenn SAS HPC:**
- [GPC2 Cluster Documentation](https://computing.sas.upenn.edu/gpc)
- [Software Environments](https://computing.sas.upenn.edu/gpc/software-environments)
- [Slurm Job Submission](https://computing.sas.upenn.edu/gpc/job/slurm)

## Note
Anthropic's Claude.ai was used to revise this README based on a earlier draft by @emery-upenn. The AI-generated revision was edited and corrected, also by @emeryr-upenn.
