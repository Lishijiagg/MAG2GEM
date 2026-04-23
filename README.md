# MAG2GEM

A pipeline for the batch reconstruction of Genome-Scale Metabolic Models (GEMs) from Metagenome-Assembled Genomes (MAGs). Designed specifically for High-Performance Computing (HPC) environments.

## Requirements

Ensure the following dependencies are installed in your environment:

* `python` >= 3.8
* `cobra` (COBRApy)
* `carveme` (Required if using the CarveMe builder)
* `gapseq` (Required if using the gapseq builder)
* `cplex` (Highly recommended for maximum speed and resolving complex gap-filling)

## Installation
We provide an automated installation script to set up the main Python environment (including CarveMe and COBRApy) via Conda/Micromamba.

### Clone the repository
```bash
git clone [https://github.com/Lishijiagg/MAG2GEM.git](https://github.com/Lishijiagg/MAG2GEM.git)
cd MAG2GEM/install
chmod +x install.sh
./install.sh
```

## Quick Start (HPC / SLURM)

For High-Performance Computing (HPC) environments, we provide a ready-to-use SLURM submission script: `run_MAG2GEM.sh`. This script automatically handles temporary directories, resource allocation, and execution logic.

### Step 1: Configure Your Paths
Open `run_MAG2GEM.sh` with a text editor (e.g., `nano run_MAG2GEM.sh`) and update the `Path setup` section to match your actual files and desired output directories:
* `MASTER_SEQ`: Path to your concatenated `.faa` file.
* `MAP_TABLE`: Path to your mapping `.tsv` or `.txt.gz` file.
* `EGGNOG_FILE`: Path to your eggNOG annotations (leave empty `""` if not needed).

### Step 2: Choose Your Engine (CarveMe vs. gapseq)
The pipeline features a dual-engine architecture. Scroll to the bottom of the `run_MAG2GEM.sh` script to the **Execution Logic** section. You can easily switch engines by commenting (`#`) or uncommenting the code blocks:

**Option A: CarveMe Mode (Default)**
* **Best for**: Ultra-fast processing of large MAG datasets with a low memory footprint.
* **How to use**: Ensure the Option A block is active (uncommented).
* **Concurrency**: Safe to set high (e.g., `-c 16`, matching your requested SLURM CPUs).

**Option B: gapseq Mode**
* **Best for**: High-detail metabolic reconstruction, strict gap-filling, and growth media prediction.
* **How to use**: Comment out Option A, and uncomment the Option B block. Ensure `--gapseq_path` is correctly set.
* **CRITICAL**: `gapseq` is extremely memory-intensive. Please allocate sufficient memory

### Step 3: Submit the Job
Once your paths and engine preferences are set, submit the script to your SLURM cluster:

```bash
sbatch run_MAG2GEM.sh