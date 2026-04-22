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

## Quick Start

### CarveMe Mode (High Speed - Default)
Ideal for processing hundreds or thousands of MAGs quickly with low memory footprint. High concurrency is safe to use.

```bash
python src/MAG2GEM_v2.py \
  -s master.fasta \
  -t mapping.tsv \
  -o ./models_carveme \
  -f ./mags \
  -e eggnog.tsv.gz \
  -c 16 \
  -b carveme
