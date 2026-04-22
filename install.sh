#!/bin/bash

echo "========================================================"
echo " Installing MAG2GEM
echo "========================================================"

if command -v micromamba &> /dev/null; then
    CONDA_CMD="micromamba"
elif command -v conda &> /dev/null; then
    CONDA_CMD="conda"
else
    echo "[Error] Conda or Micromamba was not detected! Please install first."
    exit 1
fi

echo "[INFO] Creating a virtual environment named mag2gem_env and installing dependencies (this may take few minutes)..."
$CONDA_CMD env create -f environment.yml -y

chmod +x src/MAG2GEM_v2.py

echo "========================================================"
echo "Installation successful"
echo "Please run the following command to activate the environment:"
echo "   $CONDA_CMD activate mag2gem_env"
echo ""
echo "If you need to use the gapseq engine, please refer to the official documentation to install gapseq separately."
echo "========================================================"
