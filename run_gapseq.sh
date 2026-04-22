#!/bin/bash
#SBATCH --job-name=hybrid_gem_test
#SBATCH --partition=nbi-compute
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=1-00:00:00
#SBATCH --output=gem_pipeline_%j.out
#SBATCH --error=gem_pipeline_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=zez26har@nbi.ac.uk

# ================================================
# 环境初始化
# ================================================
source ~/.bashrc
micromamba activate gapseq

# ================================================
# 临时目录配置（使用NBI scratch空间）
# ================================================
export TMPDIR="/qib/scratch/users/${USER}/gapseq_tmp_${SLURM_JOB_ID}"
mkdir -p "${TMPDIR}"
echo "[INFO] Temp directory: ${TMPDIR}"

# ================================================
# 路径配置
# ================================================
MASTER_SEQ="/qib/research-projects/fmh_RYpersistence/RY_results2/RYdata/genecat/compl.incompl.95.prot.faa"
MAP_TABLE="/qib/research-projects/fmh_RYpersistence/RY_results2/RYdata/genecat/Bin_SB/LOGandSUB/MAGvsGC.txt.gz"

XML_OUTDIR="/hpc-home/zez26har/MAGs2GEMs/gapseq_test/GEMs"
FASTA_OUTDIR="/hpc-home/zez26har/MAGs2GEMs/gapseq_test/Extracted_MAGs"

EGGNOG_FILE="/qib/research-projects/fmh_RYpersistence/RY_results2/RYdata/genecat/Anno/Func/emapper/MF.emapper.annotations.gz"

GAPSEQ_PATH="/hpc-home/zez26har/software/gapseq"
GAPSEQ_ENV="gapseq"

SCRIPT_DIR="/hpc-home/zez26har/MAGs2GEMs/gapseq_test"
SCRIPT_NAME="MAG2GEM_v2.py"

# ================================================
# 创建输出目录
# ================================================
mkdir -p ${XML_OUTDIR}
mkdir -p ${FASTA_OUTDIR}

# ================================================
# 启动信息
# ================================================
echo "=========================================="
echo "Starting Hybrid Pipeline Job"
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

# ================================================
# 组装并执行命令（测试模式：-n 3）
# ================================================
CMD="python ${SCRIPT_NAME} \
    -s ${MASTER_SEQ} \
    -t ${MAP_TABLE} \
    -o ${XML_OUTDIR} \
    -f ${FASTA_OUTDIR} \
    -c 4 \
    -b gapseq \
    -n 3 \
    --gapseq_path ${GAPSEQ_PATH} \
    --gapseq_env ${GAPSEQ_ENV}"

if [ -n "${EGGNOG_FILE}" ]; then
    CMD="${CMD} -e ${EGGNOG_FILE}"
fi

echo "Executing:"
echo "${CMD}"
echo "=========================================="

eval ${CMD}

echo "=========================================="
echo "Pipeline finished at $(date)"
echo "=========================================="