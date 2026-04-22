#!/usr/bin/env python3
import os
import sys
import gzip
import csv
import subprocess
import argparse
import shutil
from concurrent.futures import ProcessPoolExecutor

def check_solver():
    try:
        import cobra
        solver_name = cobra.Configuration().solver.__name__
        print(f"\n{'='*60}")
        print(f"[SYSTEM CHECK] Active Metabolic Solver: {solver_name}")
        if "cplex" in solver_name.lower():
            print("[STATUS] CPLEX engine is ENGAGED. Maximum speed unlocked!")
        else:
            print("[WARNING] CPLEX NOT DETECTED! Using slower fallback solver.")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n[SYSTEM CHECK] Could not verify solver setup: {e}\n")

def load_master_sequence(path):
    print(f"[INFO] Loading master sequence file into memory: {path}")
    seq_dict = {}
    with open(path,'r') as f:
        header = ""
        seq = []
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if header:
                    seq_dict[header] = "".join(seq)
                raw_header = line[1:].split()[0]
                header = raw_header[5:] if raw_header.startswith("gene_") else raw_header
                seq = []
            else:
                seq.append(line)
        if header:
            seq_dict[header] = "".join(seq)
    print(f"[SUCCESS] Loaded {len(seq_dict)} sequences into memory.")
    return seq_dict

def load_eggnog_master(path):
    print(f"[INFO] Loading master eggNOG annotations into memory: {path}")
    eggnog_dict = {}
    open_func = gzip.open if path.endswith('.gz') else open
    mode = 'rt' if path.endswith('.gz') else 'r'
    
    with open_func(path, mode, encoding='utf-8') as f:
        header = []
        for line in f:
            if line.startswith('##'): continue
            if line.startswith('#'):
                header = line.lstrip('#').strip().split('\t')
                continue
            if not line.strip(): continue
            
            parts = line.strip('\n').split('\t')
            if len(parts) < len(header):
                parts += [''] * (len(header) - len(parts))
                
            row_dict = dict(zip(header, parts))
            query_id = row_dict.get('query', '')
            if not query_id: continue
            
            clean_id = query_id[5:] if query_id.startswith("gene_") else query_id
            
            eggnog_dict[clean_id] = {
                'KEGG_ko': row_dict.get('KEGG_ko', '').replace('ko:', ''),
                'EC': row_dict.get('EC', ''),
                'Description': row_dict.get('Description', ''),
                'COG': row_dict.get('COG_category', ''),
                'PFAM': row_dict.get('PFAMs', '')
            }
            
    print(f"[SUCCESS] Loaded {len(eggnog_dict)} annotation records into memory.")
    return eggnog_dict

def run_worker(task_info):
    input_fasta, model_id, outdir, tmp_dir, primary_uni, mag_anno_subset, builder, gapseq_path, gapseq_env = task_info
    out_xml = os.path.join(outdir, f"{model_id}.xml")
    
    if os.path.exists(out_xml) and os.path.getsize(out_xml) > 1000:
        print(f"[{model_id}] [SKIP] Model already exists. Skipping...")
        return

    # ==========================================
    # ROUTE A: CARVEME PIPELINE
    # ==========================================
    if builder == "carveme":
        print(f"[{model_id}] [CarveMe] Domain: {primary_uni}. Starting CarveMe...")
        carve_bin = os.path.join(os.path.dirname(sys.executable), "carve")

        def run_carve(uni):
            cmd = [carve_bin, input_fasta, "-o", out_xml]
            if uni == "archaea":
                cmd.extend(["--universe", "archaea"])
            try:
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=1200)
                if result.returncode != 0:
                    return False, result.stderr
                return True, ""
            except subprocess.TimeoutExpired:
                return False, "TIMEOUT_EXPIRED"

        success, err_msg = run_carve(primary_uni)

        if not os.path.exists(out_xml) or os.path.getsize(out_xml) == 0:
            print(f"[{model_id}] [ERROR] {primary_uni} failed. Reason:\n{err_msg}\nInitiating fallback ...")
            fallback_uni = "archaea" if primary_uni == "bacteria" else "bacteria"
            success, err_msg_fallback = run_carve(fallback_uni)
            if not (os.path.exists(out_xml) and os.path.getsize(out_xml) > 0):
                print(f"[{model_id}] [FATAL] Both universes failed. Fallback Reason:\n{err_msg_fallback}")
                return

    # ==========================================
    # ROUTE B: GAPSEQ PIPELINE
    # ==========================================
    elif builder == "gapseq":
        print(f"[{model_id}] [gapseq] Starting hard-core metabolic reconstruction...")
        
        sandbox_dir = os.path.join(tmp_dir, f"gapseq_sandbox_{model_id}")
        os.makedirs(sandbox_dir, exist_ok=True)
        
        abs_fasta = os.path.abspath(input_fasta)
        gapseq_exe = os.path.join(gapseq_path, "gapseq")
        
        bash_cmd = f"source ~/.bashrc && micromamba activate {gapseq_env} && {gapseq_exe} doall -O -A diamond {abs_fasta}"
        cmd = ["bash", "-c", bash_cmd]
        
        try:
            result = subprocess.run(cmd, cwd=sandbox_dir, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            fasta_prefix = os.path.basename(input_fasta).rsplit('.', 1)[0]
            generated_xml = os.path.join(sandbox_dir, f"{fasta_prefix}.xml")
            
            if os.path.exists(generated_xml) and os.path.getsize(generated_xml) > 0:
                shutil.copy(generated_xml, out_xml)
                print(f"[{model_id}] [gapseq] Finished successfully. Model copied.")
            else:
                print(f"[{model_id}] [FATAL] gapseq finished but XML was not found. Error:\n{result.stderr}")
                return
        except Exception as e:
            print(f"[{model_id}] [FATAL] Subprocess execution failed: {e}")
            return

    # ==========================================
    # POST-PROCESSING: EGGNOG ANNOTATION INJECTION
    # ==========================================
    if mag_anno_subset and os.path.exists(out_xml):
        import cobra
        try:
            import logging
            logging.getLogger("cobra").setLevel(logging.ERROR)
            
            model = cobra.io.read_sbml_model(out_xml)
            annotated_count = 0
            
            for gene in model.genes:
                gene_core_id = gene.id.replace('G_', '').replace('gene_', '')
                if gene_core_id in mag_anno_subset:
                    info = mag_anno_subset[gene_core_id]
                    if info['KEGG_ko']:
                        kos = [ko.strip() for ko in info['KEGG_ko'].split(',') if ko.strip()]
                        if kos: gene.annotation['kegg.orthology'] = kos
                    if info['EC']:
                        ecs = [ec.strip() for ec in info['EC'].split(',') if ec.strip()]
                        if ecs: gene.annotation['ec-code'] = ecs
                    if info['PFAM']:
                        pfams = [pf.strip() for pf in info['PFAM'].split(',') if pf.strip()]
                        if pfams: gene.annotation['pfam'] = pfams
                            
                    notes = gene.notes
                    if info['Description'] and info['Description'] != '-':
                        notes['description'] = info['Description']
                    if info['COG'] and info['COG'] != '-':
                        notes['COG_category'] = info['COG']
                    gene.notes = notes
                    annotated_count += 1
            
            cobra.io.write_sbml_model(model, out_xml)
            print(f"[{model_id}] [SUCCESS] Model finalization complete! (Injected {annotated_count} eggNOG tags)")
        except Exception as e:
            print(f"[{model_id}] [WARNING] Model built but failed to inject annotations: {e}")
    else:
        print(f"[{model_id}] [SUCCESS] Model finalization complete! (No eggNOG annotations injected)")

def main():
    check_solver()
    
    parser = argparse.ArgumentParser(description="Hybrid Pipeline: Build GEMs using CarveMe OR gapseq, and inject eggNOG annotations.")
    parser.add_argument("-s", "--master_seq", required=True, help="Path to master sequence file.")
    parser.add_argument("-t", "--table", required=True, help="Path to mapping table.")
    parser.add_argument("-o", "--outdir", required=True, help="Output directory for .xml models.")
    parser.add_argument("-f", "--fasta_outdir", required=True, help="Output directory for MAG files.")
    parser.add_argument("-c", "--cpus", type=int, default=None, help="Number of concurrent tasks (MAGs processing in parallel).")
    parser.add_argument("-n", "--limit", type=int, default=None, help="Limit the number of MAGs (for testing).")
    parser.add_argument("-e", "--eggnog", type=str, default=None, help="Path to master emapper.annotations file.")
    
    # BUILDER SELECTION
    parser.add_argument("-b", "--builder", type=str, choices=['carveme', 'gapseq'], default='carveme', 
                        help="Choose the model building engine (default: carveme).")
    parser.add_argument("--gapseq_path", type=str, default=None, 
                        help="Absolute path to your gapseq installation folder (Required if builder is gapseq).")
    parser.add_argument("--gapseq_env", type=str, default="gapseq", 
                        help="Name of the micromamba environment for gapseq (default: gapseq).")
    
    args = parser.parse_args()

    # ==========================================
    # BUILDER WARNING & INFO BLOCK
    # ==========================================
    print(f"\n{'*' * 70}")
    if args.builder == "carveme":
        print(f"[INFO] PIPELINE SELECTED : CarveMe (Default)")
        print(f"[INFO] RESOURCE PROFILE  : High speed, low memory footprint.")
        print(f"[INFO] RECOMMENDATION    : High concurrency (-c) is safe to use.")
    elif args.builder == "gapseq":
        print(f"[WARNING] PIPELINE SELECTED : gapseq")
        print(f"[WARNING] " + "!"*50)
        print(f"[WARNING] CRITICAL RESOURCE ALERT: gapseq is EXTREMELY resource-intensive!")
        print(f"[WARNING] 1. MEMORY: Ensure HPC job requests high memory (e.g., >32GB per core).")
        print(f"[WARNING] 2. THREADS: Strongly recommend reducing concurrent tasks (-c) to avoid OOM Kills.")
        print(f"[WARNING] 3. TIME: This pipeline takes significantly longer. Extend SLURM walltime.")
        print(f"[WARNING] " + "!"*50)
    print(f"{'*' * 70}\n")

    # Pre-flight check for gapseq path
    if args.builder == "gapseq":
        if not args.gapseq_path:
            print("\n[FATAL] You selected '--builder gapseq', but did not provide '--gapseq_path'.")
            print("Please provide the path, e.g., --gapseq_path /hpc-home/zez26har/software/gapseq\n")
            sys.exit(1)
        if not os.path.exists(os.path.join(args.gapseq_path, "gapseq")):
            print(f"\n[FATAL] Could not find the 'gapseq' executable inside {args.gapseq_path}\n")
            sys.exit(1)

    threads = args.cpus if args.cpus else int(os.environ.get("SLURM_CPUS_PER_TASK", 16))
    
    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.fasta_outdir, exist_ok=True)
    scratch_base = os.environ.get("SCRATCH", os.environ.get("TMPDIR", "/tmp"))
    tmp_dir = os.path.join(scratch_base, f"{args.builder}_tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    master_db = load_master_sequence(args.master_seq)

    eggnog_dict = {}
    if args.eggnog:
        if os.path.exists(args.eggnog):
            eggnog_dict = load_eggnog_master(args.eggnog)
        else:
            print(f"[ERROR] eggNOG file not found at {args.eggnog}")
            return

    print(f"\nStep 2: Parsing mapping table, identifying domains, and extracting sequences for {args.builder.upper()}...")
    tasks = []
    
    with gzip.open(args.table, 'rt', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        species_col_idx = -1 
        
        for row_idx, row in enumerate(reader):
            if not row or len(row) < 2: continue
            if row_idx == 0:
                for i, col_name in enumerate(row):
                    if "species" in col_name.lower():
                        species_col_idx = i
                        break
                if species_col_idx == -1: species_col_idx = 7
                continue

            mag_id = row[0].strip()
            primary_uni = "bacteria"
            raw_gene_ids = set()
            
            for cell in row[1 : species_col_idx + 1]:
                if "archaea" in cell.strip().lower():
                    primary_uni = "archaea"
                    break
            for cell in row[species_col_idx + 1 :]:
                cell = cell.strip()
                if not cell: continue
                for sub_id in cell.split(','):
                    clean_id = sub_id.strip().lstrip('-')
                    if clean_id.isdigit(): raw_gene_ids.add(clean_id)
            if not raw_gene_ids: continue
            
            mag_fasta_path = os.path.join(args.fasta_outdir, f"{mag_id}.faa")
            found_count = 0
            
            with open(mag_fasta_path, 'w') as out_f:
                for gid in raw_gene_ids:
                    if gid in master_db:
                        out_f.write(f">gene_{gid}\n{master_db[gid]}\n")
                        found_count += 1
            
            if found_count > 0:
                mag_anno_subset = {}
                if eggnog_dict:
                    for gid in raw_gene_ids:
                        if gid in eggnog_dict:
                            mag_anno_subset[gid] = eggnog_dict[gid]
                
                tasks.append((mag_fasta_path, mag_id, args.outdir, tmp_dir, primary_uni, mag_anno_subset, args.builder, args.gapseq_path, args.gapseq_env))
            else:
                if os.path.exists(mag_fasta_path): os.remove(mag_fasta_path)
                
            if args.limit and len(tasks) >= args.limit:
                break

    task_count = len(tasks)
    print(f"\nSuccessfully generated {task_count} valid MAG tasks.")
    
    if task_count > 0:
        print(f"\nStep 3: Running {args.builder.upper()} Pipeline in parallel with {threads} workers...")
        with ProcessPoolExecutor(max_workers=threads) as executor:
            list(executor.map(run_worker, tasks))
    else:
        print("Error: No tasks to run.")

    print("\nAll tasks completed. Models are ready in:", args.outdir)

if __name__ == "__main__":
    main()