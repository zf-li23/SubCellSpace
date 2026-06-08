#!/bin/bash
# Migrate existing CosMx GEO projects from CosMx/P*/D*/ to CosMx_GEO/GSE*/sample_name/
# Run on cluster

COSMX_BASE="/data3/yangxr002/CosMx"
GEO_BASE="/data3/yangxr002/CosMx_GEO"

mkdir -p "$GEO_BASE"

# ============================================================
# Conflict GSEs (merged samples - use GSM range as dir name)
# ============================================================

# GSE282026 (P0011) - 13 GSMs → 3 slides
# D0011→GSM8634610-GSM8634614, D0012→GSM8634615-GSM8634619, D0013→GSM8634620-GSM8634622
mkdir -p "$GEO_BASE/GSE282026/GSM8634610-GSM8634614"
mv "$COSMX_BASE/P0011/D0011/"* "$GEO_BASE/GSE282026/GSM8634610-GSM8634614/"
mkdir -p "$GEO_BASE/GSE282026/GSM8634615-GSM8634619"
mv "$COSMX_BASE/P0011/D0012/"* "$GEO_BASE/GSE282026/GSM8634615-GSM8634619/"
mkdir -p "$GEO_BASE/GSE282026/GSM8634620-GSM8634622"
mv "$COSMX_BASE/P0011/D0013/"* "$GEO_BASE/GSE282026/GSM8634620-GSM8634622/"

# GSE289194 (P0012) - 83 GSMs → 6 FOVs
# D0014→GSM8786174-GSM8786184 (F1), D0015→GSM8786185-GSM8786198 (F2)
# D0016→GSM8786199-GSM8786213 (F3), D0017→GSM8786214-GSM8786217 (F4)
# D0018→GSM8786218-GSM8786236 (F5), D0019→GSM8786237-GSM8786256 (F6)
for pair in "D0014 GSM8786174-GSM8786184" "D0015 GSM8786185-GSM8786198" \
            "D0016 GSM8786199-GSM8786213" "D0017 GSM8786214-GSM8786217" \
            "D0018 GSM8786218-GSM8786236" "D0019 GSM8786237-GSM8786256"; do
    d=$(echo $pair | cut -d' ' -f1)
    sn=$(echo $pair | cut -d' ' -f2)
    mkdir -p "$GEO_BASE/GSE289194/$sn"
    mv "$COSMX_BASE/P0012/$d/"* "$GEO_BASE/GSE289194/$sn/"
done

# GSE277782 (P0027) - 7 GSMs → 2 slides
# D0050→GSM8529618-GSM8529620, D0051→GSM8529621-GSM8529624
mkdir -p "$GEO_BASE/GSE277782/GSM8529618-GSM8529620"
mv "$COSMX_BASE/P0027/D0050/"* "$GEO_BASE/GSE277782/GSM8529618-GSM8529620/"
mkdir -p "$GEO_BASE/GSE277782/GSM8529621-GSM8529624"
mv "$COSMX_BASE/P0027/D0051/"* "$GEO_BASE/GSE277782/GSM8529621-GSM8529624/"

# GSE283625 (P0025) - 8 GSMs → 1 merged
# D0048→GSM8668172-GSM8668179
mkdir -p "$GEO_BASE/GSE283625/GSM8668172-GSM8668179"
mv "$COSMX_BASE/P0025/D0048/"* "$GEO_BASE/GSE283625/GSM8668172-GSM8668179/"

# GSE253474 (P0036) - 116 GSMs → 4 merged (M records)
# R0884-R0915→GSM8021238-GSM8021269, R0916-R0947→GSM8021270-GSM8021301
# R0948-R0973→GSM8021302-GSM8021327, R0974-R0999→GSM8021328-GSM8021353
mkdir -p "$GEO_BASE/GSE253474/GSM8021238-GSM8021269"
for r in $(seq 884 915); do
    mv "$COSMX_BASE/P0036/R$(printf '%04d' $r)/"* "$GEO_BASE/GSE253474/GSM8021238-GSM8021269/" 2>/dev/null
done
mkdir -p "$GEO_BASE/GSE253474/GSM8021270-GSM8021301"
for r in $(seq 916 947); do
    mv "$COSMX_BASE/P0036/R$(printf '%04d' $r)/"* "$GEO_BASE/GSE253474/GSM8021270-GSM8021301/" 2>/dev/null
done
mkdir -p "$GEO_BASE/GSE253474/GSM8021302-GSM8021327"
for r in $(seq 948 973); do
    mv "$COSMX_BASE/P0036/R$(printf '%04d' $r)/"* "$GEO_BASE/GSE253474/GSM8021302-GSM8021327/" 2>/dev/null
done
mkdir -p "$GEO_BASE/GSE253474/GSM8021328-GSM8021353"
for r in $(seq 974 999); do
    mv "$COSMX_BASE/P0036/R$(printf '%04d' $r)/"* "$GEO_BASE/GSE253474/GSM8021328-GSM8021353/" 2>/dev/null
done

# ============================================================
# Simple GSEs (1 D ID → 1 GSM, or N D IDs → N GSMs)
# ============================================================

# GSE234713 (P0018) - 9 D IDs → 9 GSMs (from filename)
mkdir -p "$GEO_BASE/GSE234713"
for d in D0028 D0029 D0030 D0031 D0032 D0033 D0034 D0035 D0036; do
    gsm=$(ls "$COSMX_BASE/P0018/$d/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
    [ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE234713/$gsm" && mv "$COSMX_BASE/P0018/$d/"* "$GEO_BASE/GSE234713/$gsm/"
done

# GSE253439 (P0022) - 4 D IDs → 4 GSMs
mkdir -p "$GEO_BASE/GSE253439"
for d in D0042 D0043 D0044 D0045; do
    gsm=$(ls "$COSMX_BASE/P0022/$d/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
    [ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE253439/$gsm" && mv "$COSMX_BASE/P0022/$d/"* "$GEO_BASE/GSE253439/$gsm/"
done

# GSE263591 (P0014) - 1 D ID → 1 GSM
mkdir -p "$GEO_BASE/GSE263591"
gsm=$(ls "$COSMX_BASE/P0014/D0021/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
[ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE263591/$gsm" && mv "$COSMX_BASE/P0014/D0021/"* "$GEO_BASE/GSE263591/$gsm/"

# GSE273530 (P0024) - 1 D ID → 1 GSM
mkdir -p "$GEO_BASE/GSE273530"
gsm=$(ls "$COSMX_BASE/P0024/D0047/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
[ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE273530/$gsm" && mv "$COSMX_BASE/P0024/D0047/"* "$GEO_BASE/GSE273530/$gsm/"

# GSE277441 (P0032) - 3 D IDs → 3 GSMs
mkdir -p "$GEO_BASE/GSE277441"
for d in D0060 D0061 D0062; do
    gsm=$(ls "$COSMX_BASE/P0032/$d/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
    [ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE277441/$gsm" && mv "$COSMX_BASE/P0032/$d/"* "$GEO_BASE/GSE277441/$gsm/"
done

# GSE278766 (P0015) - 1 D ID → 1 GSM
mkdir -p "$GEO_BASE/GSE278766"
gsm=$(ls "$COSMX_BASE/P0015/D0022/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
[ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE278766/$gsm" && mv "$COSMX_BASE/P0015/D0022/"* "$GEO_BASE/GSE278766/$gsm/"

# GSE282059 (P0021) - 1 D ID → GSM8635038 (from API)
mkdir -p "$GEO_BASE/GSE282059/GSM8635038"
mv "$COSMX_BASE/P0021/D0041/"* "$GEO_BASE/GSE282059/GSM8635038/"

# GSE283863 (P0017) - 1 D ID → 1 GSM
mkdir -p "$GEO_BASE/GSE283863"
gsm=$(ls "$COSMX_BASE/P0017/D0027/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
[ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE283863/$gsm" && mv "$COSMX_BASE/P0017/D0027/"* "$GEO_BASE/GSE283863/$gsm/"

# GSE286935 (P0013) - 1 D ID → 1 GSM
mkdir -p "$GEO_BASE/GSE286935"
gsm=$(ls "$COSMX_BASE/P0013/D0020/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
[ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE286935/$gsm" && mv "$COSMX_BASE/P0013/D0020/"* "$GEO_BASE/GSE286935/$gsm/"

# GSE291308 (P0026) - 1 D ID → GSM8833258 (from filename)
mkdir -p "$GEO_BASE/GSE291308/GSM8833258"
mv "$COSMX_BASE/P0026/D0049/"* "$GEO_BASE/GSE291308/GSM8833258/"

# GSE292268 (P0028) - 2 D IDs → 2 GSMs
mkdir -p "$GEO_BASE/GSE292268"
for d in D0052 D0053; do
    gsm=$(ls "$COSMX_BASE/P0028/$d/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
    [ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE292268/$gsm" && mv "$COSMX_BASE/P0028/$d/"* "$GEO_BASE/GSE292268/$gsm/"
done

# GSE299786 (P0016) - 4 D IDs → 4 GSMs
mkdir -p "$GEO_BASE/GSE299786"
for d in D0023 D0024 D0025 D0026; do
    gsm=$(ls "$COSMX_BASE/P0016/$d/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
    [ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE299786/$gsm" && mv "$COSMX_BASE/P0016/$d/"* "$GEO_BASE/GSE299786/$gsm/"
done

# GSE304111 (P0029) - 1 D ID → 1 GSM
mkdir -p "$GEO_BASE/GSE304111"
gsm=$(ls "$COSMX_BASE/P0029/D0054/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
[ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE304111/$gsm" && mv "$COSMX_BASE/P0029/D0054/"* "$GEO_BASE/GSE304111/$gsm/"

# GSE304160 (P0030) - 4 D IDs → 4 GSMs
mkdir -p "$GEO_BASE/GSE304160"
for d in D0055 D0056 D0057 D0058; do
    gsm=$(ls "$COSMX_BASE/P0030/$d/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
    [ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE304160/$gsm" && mv "$COSMX_BASE/P0030/$d/"* "$GEO_BASE/GSE304160/$gsm/"
done

# GSE305393 (P0019) - 2 D IDs → 2 GSMs
mkdir -p "$GEO_BASE/GSE305393"
for d in D0037 D0038; do
    gsm=$(ls "$COSMX_BASE/P0019/$d/"*tx_file* 2>/dev/null | head -1 | grep -oP 'GSM[0-9]+' | head -1)
    [ -n "$gsm" ] && mkdir -p "$GEO_BASE/GSE305393/$gsm" && mv "$COSMX_BASE/P0019/$d/"* "$GEO_BASE/GSE305393/$gsm/"
done

# GSE305978 (P0031) - 1 D ID → GSM9190966 (from filename)
mkdir -p "$GEO_BASE/GSE305978/GSM9190966"
mv "$COSMX_BASE/P0031/D0059/"* "$GEO_BASE/GSE305978/GSM9190966/"

# ============================================================
# Also migrate M records from P0036 to GSE253474
# ============================================================
# M0005→GSM8021238-GSM8021269 (already created above), M0006→GSM8021270-GSM8021301
# M0007→GSM8021302-GSM8021327, M0008→GSM8021328-GSM8021353
# Merge M content into same dirs (they contain merged files)
for pair in "M0005 GSM8021238-GSM8021269" "M0006 GSM8021270-GSM8021301" \
            "M0007 GSM8021302-GSM8021327" "M0008 GSM8021328-GSM8021353"; do
    m=$(echo $pair | cut -d' ' -f1)
    sn=$(echo $pair | cut -d' ' -f2)
    if [ -d "$COSMX_BASE/P0036/$m" ]; then
        cp -n "$COSMX_BASE/P0036/$m/"* "$GEO_BASE/GSE253474/$sn/" 2>/dev/null
    fi
done

echo "=== Migration complete ==="
echo "Listing target dirs:"
for gse in $(ls "$GEO_BASE"); do
    nsamples=$(ls -d "$GEO_BASE/$gse/"*/ 2>/dev/null | wc -l)
    echo "  $gse: $nsamples samples"
done
