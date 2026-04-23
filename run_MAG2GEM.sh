#!/bin/bash
#SBATCH --job-name=MAG2GEM_pipeline
#SBATCH --partition=nbi-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=1-00:00:00
#SBATCH --output=gem_pipeline_%j.out
#SBATCH --error=gem_pipeline_%j.err
#SBATCH --mail-type=END,FAIL

source ~/.bashrc
export PYTHONNOUSERSITE=1
micromamba activate CarveMe_stable

# ================================================
# Temporal directory setup
# ================================================
export TMPDIR="/qib/scratch/users/${USER}/mag2gem_tmp_${SLURM_JOB_ID}"
mkdir -p "${TMPDIR}"
echo "[INFO] Temp directory: ${TMPDIR}"

# ================================================
# Path setup
# ================================================
MASTER_SEQ="/qib/research-projects/fmh_RYpersistence/RY_results2/RYdata/genecat/compl.incompl.95.prot.faa"
MAP_TABLE="/qib/research-projects/fmh_RYpersistence/RY_results2/RYdata/genecat/Bin_SB/LOGandSUB/MAGvsGC.txt.gz"

XML_OUTDIR="/hpc-home/zez26har/MAGs2GEMs/gapseq_test/GEMs_Output_gapseq"
FASTA_OUTDIR="/hpc-home/zez26har/MAGs2GEMs/gapseq_test/Extracted_MAGs_Output_gapseq"

# If no eggnog annotation, set EGGNOG_FILE=""
EGGNOG_FILE="/qib/research-projects/fmh_RYpersistence/RY_results2/RYdata/genecat/Anno/Func/emapper/MF.emapper.annotations.gz"

GAPSEQ_PATH="/hpc-home/zez26har/software/gapseq"
GAPSEQ_ENV="gapseq"

SCRIPT_DIR="/hpc-home/zez26har/MAGs2GEMs/gapseq_test"
SCRIPT_NAME="MAG2GEM_v2.py"

# ================================================
# Create output directories if they don't exist
# ================================================
mkdir -p ${XML_OUTDIR}
mkdir -p ${FASTA_OUTDIR}

echo "=========================================="
echo "Starting MAG2GEM Pipeline Job"
echo "Start time:      $(date)"
echo "Job ID:          ${SLURM_JOB_ID}"
echo "Node:            $(hostname)"
echo "CPUs allocated:  ${SLURM_CPUS_PER_TASK}"
echo "Temp dir:        ${TMPDIR}"
echo "Master sequence: ${MASTER_SEQ}"
echo "Mapping table:   ${MAP_TABLE}"
echo "Output models:   ${XML_OUTDIR}"
echo "=========================================="

cd ${SCRIPT_DIR}

# Optional eggnog arguments
EGGNOG_ARG=""
if [ -n "${EGGNOG_FILE}" ]; then
    EGGNOG_ARG="-e ${EGGNOG_FILE}"
fi

# ================================================
# Execution Logic (Choose your engine)
# ================================================

# ------------------------------------------------
# OPTION A: CarveMe Engine (Current Active)
# ------------------------------------------------
# echo "[INFO] Executing CarveMe Pipeline..."
# python ${SCRIPT_NAME} \
#     -s ${MASTER_SEQ} \
#     -t ${MAP_TABLE} \
#     -o ${XML_OUTDIR} \
#     -f ${FASTA_OUTDIR} \
#     ${EGGNOG_ARG} \
#     -c 16 \
#     -b carveme

# ------------------------------------------------
# OPTION B: gapseq Engine (Currently Commented Out)
# ------------------------------------------------
 echo "[INFO] Executing gapseq Pipeline..."
 python ${SCRIPT_NAME} \
     -s ${MASTER_SEQ} \
     -t ${MAP_TABLE} \
     -o ${XML_OUTDIR} \
     -f ${FASTA_OUTDIR} \
     ${EGGNOG_ARG} \
     -c 4 \
     -b gapseq \
     --gapseq_path ${GAPSEQ_PATH} \
     --gapseq_env ${GAPSEQ_ENV}

echo "=========================================="
echo "Pipeline finished at $(date)"
echo "=========================================="
