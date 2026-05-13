#!/bin/bash
#SBATCH --job-name=xen_extract
#SBATCH --output=/data3/yangxr002/Xenium/_logs/%x_%a.out
#SBATCH --error=/data3/yangxr002/Xenium/_logs/%x_%a.err
#SBATCH --cpus-per-task=1
#SBATCH --mem=500M
#SBATCH --time=04:00:00

#SBATCH --array=1-36

mkdir -p /data3/yangxr002/Xenium/_logs

TAR_DIR="/data3/yangxr002/Xenium"
TASK_ID=$SLURM_ARRAY_TASK_ID

# Mapping of task_id -> (id, tar_file, dest)
case $TASK_ID in
  1)
  echo "== [D1090] Extracting GSE250346_RAW.tar to /data3/yangxr002/Xenium/P1051/D1090 =="
  rm -rf "/data3/yangxr002/Xenium/P1051/D1090"/*
  mkdir -p "/data3/yangxr002/Xenium/P1051/D1090"
  if [ -f "/data3/yangxr002/Xenium/GSE250346_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE250346_RAW.tar" -C "/data3/yangxr002/Xenium/P1051/D1090"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1051/D1090" | wc -l)
      echo "  [D1090] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1051/D1090"/*
      echo "  [D1090] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1090] MISSING TAR: /data3/yangxr002/Xenium/GSE250346_RAW.tar"
    exit 1
  fi
  ;;
  2)
  echo "== [D1091] Extracting GSE251937_RAW.tar to /data3/yangxr002/Xenium/P1052/D1091 =="
  rm -rf "/data3/yangxr002/Xenium/P1052/D1091"/*
  mkdir -p "/data3/yangxr002/Xenium/P1052/D1091"
  if [ -f "/data3/yangxr002/Xenium/GSE251937_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE251937_RAW.tar" -C "/data3/yangxr002/Xenium/P1052/D1091"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1052/D1091" | wc -l)
      echo "  [D1091] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1052/D1091"/*
      echo "  [D1091] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1091] MISSING TAR: /data3/yangxr002/Xenium/GSE251937_RAW.tar"
    exit 1
  fi
  ;;
  3)
  echo "== [D1092] Extracting GSE251938_RAW.tar to /data3/yangxr002/Xenium/P1053/D1092 =="
  rm -rf "/data3/yangxr002/Xenium/P1053/D1092"/*
  mkdir -p "/data3/yangxr002/Xenium/P1053/D1092"
  if [ -f "/data3/yangxr002/Xenium/GSE251938_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE251938_RAW.tar" -C "/data3/yangxr002/Xenium/P1053/D1092"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1053/D1092" | wc -l)
      echo "  [D1092] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1053/D1092"/*
      echo "  [D1092] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1092] MISSING TAR: /data3/yangxr002/Xenium/GSE251938_RAW.tar"
    exit 1
  fi
  ;;
  4)
  echo "== [D1094] Extracting GSE263498_RAW.tar to /data3/yangxr002/Xenium/P1055/D1094 =="
  rm -rf "/data3/yangxr002/Xenium/P1055/D1094"/*
  mkdir -p "/data3/yangxr002/Xenium/P1055/D1094"
  if [ -f "/data3/yangxr002/Xenium/GSE263498_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE263498_RAW.tar" -C "/data3/yangxr002/Xenium/P1055/D1094"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1055/D1094" | wc -l)
      echo "  [D1094] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1055/D1094"/*
      echo "  [D1094] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1094] MISSING TAR: /data3/yangxr002/Xenium/GSE263498_RAW.tar"
    exit 1
  fi
  ;;
  5)
  echo "== [D1095] Extracting GSE264334_RAW.tar to /data3/yangxr002/Xenium/P1056/D1095 =="
  rm -rf "/data3/yangxr002/Xenium/P1056/D1095"/*
  mkdir -p "/data3/yangxr002/Xenium/P1056/D1095"
  if [ -f "/data3/yangxr002/Xenium/GSE264334_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE264334_RAW.tar" -C "/data3/yangxr002/Xenium/P1056/D1095"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1056/D1095" | wc -l)
      echo "  [D1095] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1056/D1095"/*
      echo "  [D1095] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1095] MISSING TAR: /data3/yangxr002/Xenium/GSE264334_RAW.tar"
    exit 1
  fi
  ;;
  6)
  echo "== [D1097] Extracting GSE267680_RAW.tar to /data3/yangxr002/Xenium/P1058/D1097 =="
  rm -rf "/data3/yangxr002/Xenium/P1058/D1097"/*
  mkdir -p "/data3/yangxr002/Xenium/P1058/D1097"
  if [ -f "/data3/yangxr002/Xenium/GSE267680_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE267680_RAW.tar" -C "/data3/yangxr002/Xenium/P1058/D1097"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1058/D1097" | wc -l)
      echo "  [D1097] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1058/D1097"/*
      echo "  [D1097] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1097] MISSING TAR: /data3/yangxr002/Xenium/GSE267680_RAW.tar"
    exit 1
  fi
  ;;
  7)
  echo "== [D1098] Extracting GSE269354_RAW.tar to /data3/yangxr002/Xenium/P1059/D1098 =="
  rm -rf "/data3/yangxr002/Xenium/P1059/D1098"/*
  mkdir -p "/data3/yangxr002/Xenium/P1059/D1098"
  if [ -f "/data3/yangxr002/Xenium/GSE269354_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE269354_RAW.tar" -C "/data3/yangxr002/Xenium/P1059/D1098"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1059/D1098" | wc -l)
      echo "  [D1098] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1059/D1098"/*
      echo "  [D1098] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1098] MISSING TAR: /data3/yangxr002/Xenium/GSE269354_RAW.tar"
    exit 1
  fi
  ;;
  8)
  echo "== [D1099] Extracting GSE270437_RAW.tar to /data3/yangxr002/Xenium/P1060/D1099 =="
  rm -rf "/data3/yangxr002/Xenium/P1060/D1099"/*
  mkdir -p "/data3/yangxr002/Xenium/P1060/D1099"
  if [ -f "/data3/yangxr002/Xenium/GSE270437_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE270437_RAW.tar" -C "/data3/yangxr002/Xenium/P1060/D1099"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1060/D1099" | wc -l)
      echo "  [D1099] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1060/D1099"/*
      echo "  [D1099] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1099] MISSING TAR: /data3/yangxr002/Xenium/GSE270437_RAW.tar"
    exit 1
  fi
  ;;
  9)
  echo "== [D1101] Extracting GSE273557_RAW.tar to /data3/yangxr002/Xenium/P1062/D1101 =="
  rm -rf "/data3/yangxr002/Xenium/P1062/D1101"/*
  mkdir -p "/data3/yangxr002/Xenium/P1062/D1101"
  if [ -f "/data3/yangxr002/Xenium/GSE273557_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE273557_RAW.tar" -C "/data3/yangxr002/Xenium/P1062/D1101"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1062/D1101" | wc -l)
      echo "  [D1101] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1062/D1101"/*
      echo "  [D1101] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1101] MISSING TAR: /data3/yangxr002/Xenium/GSE273557_RAW.tar"
    exit 1
  fi
  ;;
  10)
  echo "== [D1106] Extracting GSE278969_RAW.tar to /data3/yangxr002/Xenium/P1067/D1106 =="
  rm -rf "/data3/yangxr002/Xenium/P1067/D1106"/*
  mkdir -p "/data3/yangxr002/Xenium/P1067/D1106"
  if [ -f "/data3/yangxr002/Xenium/GSE278969_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE278969_RAW.tar" -C "/data3/yangxr002/Xenium/P1067/D1106"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1067/D1106" | wc -l)
      echo "  [D1106] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1067/D1106"/*
      echo "  [D1106] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1106] MISSING TAR: /data3/yangxr002/Xenium/GSE278969_RAW.tar"
    exit 1
  fi
  ;;
  11)
  echo "== [D1114] Extracting GSE283832_RAW.tar to /data3/yangxr002/Xenium/P1075/D1114 =="
  rm -rf "/data3/yangxr002/Xenium/P1075/D1114"/*
  mkdir -p "/data3/yangxr002/Xenium/P1075/D1114"
  if [ -f "/data3/yangxr002/Xenium/GSE283832_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE283832_RAW.tar" -C "/data3/yangxr002/Xenium/P1075/D1114"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1075/D1114" | wc -l)
      echo "  [D1114] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1075/D1114"/*
      echo "  [D1114] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1114] MISSING TAR: /data3/yangxr002/Xenium/GSE283832_RAW.tar"
    exit 1
  fi
  ;;
  12)
  echo "== [D1115] Extracting GSE283843_RAW.tar to /data3/yangxr002/Xenium/P1076/D1115 =="
  rm -rf "/data3/yangxr002/Xenium/P1076/D1115"/*
  mkdir -p "/data3/yangxr002/Xenium/P1076/D1115"
  if [ -f "/data3/yangxr002/Xenium/GSE283843_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE283843_RAW.tar" -C "/data3/yangxr002/Xenium/P1076/D1115"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1076/D1115" | wc -l)
      echo "  [D1115] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1076/D1115"/*
      echo "  [D1115] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1115] MISSING TAR: /data3/yangxr002/Xenium/GSE283843_RAW.tar"
    exit 1
  fi
  ;;
  13)
  echo "== [D1116] Extracting GSE285984_RAW.tar to /data3/yangxr002/Xenium/P1077/D1116 =="
  rm -rf "/data3/yangxr002/Xenium/P1077/D1116"/*
  mkdir -p "/data3/yangxr002/Xenium/P1077/D1116"
  if [ -f "/data3/yangxr002/Xenium/GSE285984_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE285984_RAW.tar" -C "/data3/yangxr002/Xenium/P1077/D1116"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1077/D1116" | wc -l)
      echo "  [D1116] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1077/D1116"/*
      echo "  [D1116] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1116] MISSING TAR: /data3/yangxr002/Xenium/GSE285984_RAW.tar"
    exit 1
  fi
  ;;
  14)
  echo "== [D1118] Extracting GSE286422_RAW.tar to /data3/yangxr002/Xenium/P1079/D1118 =="
  rm -rf "/data3/yangxr002/Xenium/P1079/D1118"/*
  mkdir -p "/data3/yangxr002/Xenium/P1079/D1118"
  if [ -f "/data3/yangxr002/Xenium/GSE286422_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE286422_RAW.tar" -C "/data3/yangxr002/Xenium/P1079/D1118"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1079/D1118" | wc -l)
      echo "  [D1118] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1079/D1118"/*
      echo "  [D1118] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1118] MISSING TAR: /data3/yangxr002/Xenium/GSE286422_RAW.tar"
    exit 1
  fi
  ;;
  15)
  echo "== [D1123] Extracting GSE291246_RAW.tar to /data3/yangxr002/Xenium/P1084/D1123 =="
  rm -rf "/data3/yangxr002/Xenium/P1084/D1123"/*
  mkdir -p "/data3/yangxr002/Xenium/P1084/D1123"
  if [ -f "/data3/yangxr002/Xenium/GSE291246_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE291246_RAW.tar" -C "/data3/yangxr002/Xenium/P1084/D1123"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1084/D1123" | wc -l)
      echo "  [D1123] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1084/D1123"/*
      echo "  [D1123] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1123] MISSING TAR: /data3/yangxr002/Xenium/GSE291246_RAW.tar"
    exit 1
  fi
  ;;
  16)
  echo "== [D1127] Extracting GSE293759_RAW.tar to /data3/yangxr002/Xenium/P1088/D1127 =="
  rm -rf "/data3/yangxr002/Xenium/P1088/D1127"/*
  mkdir -p "/data3/yangxr002/Xenium/P1088/D1127"
  if [ -f "/data3/yangxr002/Xenium/GSE293759_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE293759_RAW.tar" -C "/data3/yangxr002/Xenium/P1088/D1127"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1088/D1127" | wc -l)
      echo "  [D1127] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1088/D1127"/*
      echo "  [D1127] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1127] MISSING TAR: /data3/yangxr002/Xenium/GSE293759_RAW.tar"
    exit 1
  fi
  ;;
  17)
  echo "== [D1129] Extracting GSE293970_RAW.tar to /data3/yangxr002/Xenium/P1090/D1129 =="
  rm -rf "/data3/yangxr002/Xenium/P1090/D1129"/*
  mkdir -p "/data3/yangxr002/Xenium/P1090/D1129"
  if [ -f "/data3/yangxr002/Xenium/GSE293970_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE293970_RAW.tar" -C "/data3/yangxr002/Xenium/P1090/D1129"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1090/D1129" | wc -l)
      echo "  [D1129] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1090/D1129"/*
      echo "  [D1129] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1129] MISSING TAR: /data3/yangxr002/Xenium/GSE293970_RAW.tar"
    exit 1
  fi
  ;;
  18)
  echo "== [D1130] Extracting GSE293972_RAW.tar to /data3/yangxr002/Xenium/P1091/D1130 =="
  rm -rf "/data3/yangxr002/Xenium/P1091/D1130"/*
  mkdir -p "/data3/yangxr002/Xenium/P1091/D1130"
  if [ -f "/data3/yangxr002/Xenium/GSE293972_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE293972_RAW.tar" -C "/data3/yangxr002/Xenium/P1091/D1130"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1091/D1130" | wc -l)
      echo "  [D1130] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1091/D1130"/*
      echo "  [D1130] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1130] MISSING TAR: /data3/yangxr002/Xenium/GSE293972_RAW.tar"
    exit 1
  fi
  ;;
  19)
  echo "== [D1141] Extracting GSE300007_RAW.tar to /data3/yangxr002/Xenium/P1102/D1141 =="
  rm -rf "/data3/yangxr002/Xenium/P1102/D1141"/*
  mkdir -p "/data3/yangxr002/Xenium/P1102/D1141"
  if [ -f "/data3/yangxr002/Xenium/GSE300007_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE300007_RAW.tar" -C "/data3/yangxr002/Xenium/P1102/D1141"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1102/D1141" | wc -l)
      echo "  [D1141] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1102/D1141"/*
      echo "  [D1141] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1141] MISSING TAR: /data3/yangxr002/Xenium/GSE300007_RAW.tar"
    exit 1
  fi
  ;;
  20)
  echo "== [D1158] Extracting GSE308699_RAW.tar to /data3/yangxr002/Xenium/P1119/D1158 =="
  rm -rf "/data3/yangxr002/Xenium/P1119/D1158"/*
  mkdir -p "/data3/yangxr002/Xenium/P1119/D1158"
  if [ -f "/data3/yangxr002/Xenium/GSE308699_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE308699_RAW.tar" -C "/data3/yangxr002/Xenium/P1119/D1158"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1119/D1158" | wc -l)
      echo "  [D1158] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1119/D1158"/*
      echo "  [D1158] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1158] MISSING TAR: /data3/yangxr002/Xenium/GSE308699_RAW.tar"
    exit 1
  fi
  ;;
  21)
  echo "== [D1166] Extracting GSE313662_RAW.tar to /data3/yangxr002/Xenium/P1127/D1166 =="
  rm -rf "/data3/yangxr002/Xenium/P1127/D1166"/*
  mkdir -p "/data3/yangxr002/Xenium/P1127/D1166"
  if [ -f "/data3/yangxr002/Xenium/GSE313662_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE313662_RAW.tar" -C "/data3/yangxr002/Xenium/P1127/D1166"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1127/D1166" | wc -l)
      echo "  [D1166] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1127/D1166"/*
      echo "  [D1166] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1166] MISSING TAR: /data3/yangxr002/Xenium/GSE313662_RAW.tar"
    exit 1
  fi
  ;;
  22)
  echo "== [D1168] Extracting GSE315246_RAW.tar to /data3/yangxr002/Xenium/P1129/D1168 =="
  rm -rf "/data3/yangxr002/Xenium/P1129/D1168"/*
  mkdir -p "/data3/yangxr002/Xenium/P1129/D1168"
  if [ -f "/data3/yangxr002/Xenium/GSE315246_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE315246_RAW.tar" -C "/data3/yangxr002/Xenium/P1129/D1168"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1129/D1168" | wc -l)
      echo "  [D1168] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1129/D1168"/*
      echo "  [D1168] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1168] MISSING TAR: /data3/yangxr002/Xenium/GSE315246_RAW.tar"
    exit 1
  fi
  ;;
  23)
  echo "== [D1175] Extracting GSE322974_RAW.tar to /data3/yangxr002/Xenium/P1136/D1175 =="
  rm -rf "/data3/yangxr002/Xenium/P1136/D1175"/*
  mkdir -p "/data3/yangxr002/Xenium/P1136/D1175"
  if [ -f "/data3/yangxr002/Xenium/GSE322974_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE322974_RAW.tar" -C "/data3/yangxr002/Xenium/P1136/D1175"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1136/D1175" | wc -l)
      echo "  [D1175] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1136/D1175"/*
      echo "  [D1175] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1175] MISSING TAR: /data3/yangxr002/Xenium/GSE322974_RAW.tar"
    exit 1
  fi
  ;;
  24)
  echo "== [D1181] Extracting GSE326837_RAW.tar to /data3/yangxr002/Xenium/P1142/D1181 =="
  rm -rf "/data3/yangxr002/Xenium/P1142/D1181"/*
  mkdir -p "/data3/yangxr002/Xenium/P1142/D1181"
  if [ -f "/data3/yangxr002/Xenium/GSE326837_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE326837_RAW.tar" -C "/data3/yangxr002/Xenium/P1142/D1181"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1142/D1181" | wc -l)
      echo "  [D1181] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1142/D1181"/*
      echo "  [D1181] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1181] MISSING TAR: /data3/yangxr002/Xenium/GSE326837_RAW.tar"
    exit 1
  fi
  ;;
  25)
  echo "== [D1197] Extracting GSE277463_RAW.tar to /data3/yangxr002/Xenium/P1158/D1197 =="
  rm -rf "/data3/yangxr002/Xenium/P1158/D1197"/*
  mkdir -p "/data3/yangxr002/Xenium/P1158/D1197"
  if [ -f "/data3/yangxr002/Xenium/GSE277463_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE277463_RAW.tar" -C "/data3/yangxr002/Xenium/P1158/D1197"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1158/D1197" | wc -l)
      echo "  [D1197] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1158/D1197"/*
      echo "  [D1197] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1197] MISSING TAR: /data3/yangxr002/Xenium/GSE277463_RAW.tar"
    exit 1
  fi
  ;;
  26)
  echo "== [D1208] Extracting GSE284741_RAW.tar to /data3/yangxr002/Xenium/P1168/D1208 =="
  rm -rf "/data3/yangxr002/Xenium/P1168/D1208"/*
  mkdir -p "/data3/yangxr002/Xenium/P1168/D1208"
  if [ -f "/data3/yangxr002/Xenium/GSE284741_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE284741_RAW.tar" -C "/data3/yangxr002/Xenium/P1168/D1208"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1168/D1208" | wc -l)
      echo "  [D1208] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1168/D1208"/*
      echo "  [D1208] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1208] MISSING TAR: /data3/yangxr002/Xenium/GSE284741_RAW.tar"
    exit 1
  fi
  ;;
  27)
  echo "== [D1215] Extracting GSE286129_RAW.tar to /data3/yangxr002/Xenium/P1175/D1215 =="
  rm -rf "/data3/yangxr002/Xenium/P1175/D1215"/*
  mkdir -p "/data3/yangxr002/Xenium/P1175/D1215"
  if [ -f "/data3/yangxr002/Xenium/GSE286129_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE286129_RAW.tar" -C "/data3/yangxr002/Xenium/P1175/D1215"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1175/D1215" | wc -l)
      echo "  [D1215] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1175/D1215"/*
      echo "  [D1215] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1215] MISSING TAR: /data3/yangxr002/Xenium/GSE286129_RAW.tar"
    exit 1
  fi
  ;;
  28)
  echo "== [D1218] Extracting GSE289263_RAW.tar to /data3/yangxr002/Xenium/P1178/D1218 =="
  rm -rf "/data3/yangxr002/Xenium/P1178/D1218"/*
  mkdir -p "/data3/yangxr002/Xenium/P1178/D1218"
  if [ -f "/data3/yangxr002/Xenium/GSE289263_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE289263_RAW.tar" -C "/data3/yangxr002/Xenium/P1178/D1218"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1178/D1218" | wc -l)
      echo "  [D1218] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1178/D1218"/*
      echo "  [D1218] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1218] MISSING TAR: /data3/yangxr002/Xenium/GSE289263_RAW.tar"
    exit 1
  fi
  ;;
  29)
  echo "== [D1233] Extracting GSE299195_RAW.tar to /data3/yangxr002/Xenium/P1192/D1233 =="
  rm -rf "/data3/yangxr002/Xenium/P1192/D1233"/*
  mkdir -p "/data3/yangxr002/Xenium/P1192/D1233"
  if [ -f "/data3/yangxr002/Xenium/GSE299195_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE299195_RAW.tar" -C "/data3/yangxr002/Xenium/P1192/D1233"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1192/D1233" | wc -l)
      echo "  [D1233] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1192/D1233"/*
      echo "  [D1233] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1233] MISSING TAR: /data3/yangxr002/Xenium/GSE299195_RAW.tar"
    exit 1
  fi
  ;;
  30)
  echo "== [D1241] Extracting GSE302473_RAW.tar to /data3/yangxr002/Xenium/P1198/D1241 =="
  rm -rf "/data3/yangxr002/Xenium/P1198/D1241"/*
  mkdir -p "/data3/yangxr002/Xenium/P1198/D1241"
  if [ -f "/data3/yangxr002/Xenium/GSE302473_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE302473_RAW.tar" -C "/data3/yangxr002/Xenium/P1198/D1241"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1198/D1241" | wc -l)
      echo "  [D1241] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1198/D1241"/*
      echo "  [D1241] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1241] MISSING TAR: /data3/yangxr002/Xenium/GSE302473_RAW.tar"
    exit 1
  fi
  ;;
  31)
  echo "== [D1248] Extracting GSE309522_RAW.tar to /data3/yangxr002/Xenium/P1205/D1248 =="
  rm -rf "/data3/yangxr002/Xenium/P1205/D1248"/*
  mkdir -p "/data3/yangxr002/Xenium/P1205/D1248"
  if [ -f "/data3/yangxr002/Xenium/GSE309522_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE309522_RAW.tar" -C "/data3/yangxr002/Xenium/P1205/D1248"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1205/D1248" | wc -l)
      echo "  [D1248] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1205/D1248"/*
      echo "  [D1248] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1248] MISSING TAR: /data3/yangxr002/Xenium/GSE309522_RAW.tar"
    exit 1
  fi
  ;;
  32)
  echo "== [D1250] Extracting GSE310658_RAW.tar to /data3/yangxr002/Xenium/P1207/D1250 =="
  rm -rf "/data3/yangxr002/Xenium/P1207/D1250"/*
  mkdir -p "/data3/yangxr002/Xenium/P1207/D1250"
  if [ -f "/data3/yangxr002/Xenium/GSE310658_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE310658_RAW.tar" -C "/data3/yangxr002/Xenium/P1207/D1250"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1207/D1250" | wc -l)
      echo "  [D1250] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1207/D1250"/*
      echo "  [D1250] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1250] MISSING TAR: /data3/yangxr002/Xenium/GSE310658_RAW.tar"
    exit 1
  fi
  ;;
  33)
  echo "== [D1259] Extracting GSE316666_RAW.tar to /data3/yangxr002/Xenium/P1215/D1259 =="
  rm -rf "/data3/yangxr002/Xenium/P1215/D1259"/*
  mkdir -p "/data3/yangxr002/Xenium/P1215/D1259"
  if [ -f "/data3/yangxr002/Xenium/GSE316666_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE316666_RAW.tar" -C "/data3/yangxr002/Xenium/P1215/D1259"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1215/D1259" | wc -l)
      echo "  [D1259] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1215/D1259"/*
      echo "  [D1259] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1259] MISSING TAR: /data3/yangxr002/Xenium/GSE316666_RAW.tar"
    exit 1
  fi
  ;;
  34)
  echo "== [D1264] Extracting GSE320403_RAW.tar to /data3/yangxr002/Xenium/P1220/D1264 =="
  rm -rf "/data3/yangxr002/Xenium/P1220/D1264"/*
  mkdir -p "/data3/yangxr002/Xenium/P1220/D1264"
  if [ -f "/data3/yangxr002/Xenium/GSE320403_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE320403_RAW.tar" -C "/data3/yangxr002/Xenium/P1220/D1264"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1220/D1264" | wc -l)
      echo "  [D1264] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1220/D1264"/*
      echo "  [D1264] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1264] MISSING TAR: /data3/yangxr002/Xenium/GSE320403_RAW.tar"
    exit 1
  fi
  ;;
  35)
  echo "== [D1268] Extracting GSE328169_RAW.tar to /data3/yangxr002/Xenium/P1224/D1268 =="
  rm -rf "/data3/yangxr002/Xenium/P1224/D1268"/*
  mkdir -p "/data3/yangxr002/Xenium/P1224/D1268"
  if [ -f "/data3/yangxr002/Xenium/GSE328169_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE328169_RAW.tar" -C "/data3/yangxr002/Xenium/P1224/D1268"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1224/D1268" | wc -l)
      echo "  [D1268] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1224/D1268"/*
      echo "  [D1268] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1268] MISSING TAR: /data3/yangxr002/Xenium/GSE328169_RAW.tar"
    exit 1
  fi
  ;;
  36)
  echo "== [D1270] Extracting GSE329229_RAW.tar to /data3/yangxr002/Xenium/P1226/D1270 =="
  rm -rf "/data3/yangxr002/Xenium/P1226/D1270"/*
  mkdir -p "/data3/yangxr002/Xenium/P1226/D1270"
  if [ -f "/data3/yangxr002/Xenium/GSE329229_RAW.tar" ]; then
    tar -xf "/data3/yangxr002/Xenium/GSE329229_RAW.tar" -C "/data3/yangxr002/Xenium/P1226/D1270"
    if [ $? -eq 0 ]; then
      CNT=$(ls "/data3/yangxr002/Xenium/P1226/D1270" | wc -l)
      echo "  [D1270] OK: $CNT files"
    else
      rm -rf "/data3/yangxr002/Xenium/P1226/D1270"/*
      echo "  [D1270] FAILED: tar error"
      exit 1
    fi
  else
    echo "  [D1270] MISSING TAR: /data3/yangxr002/Xenium/GSE329229_RAW.tar"
    exit 1
  fi
  ;;
  *)
    echo "Unknown task $TASK_ID"
    exit 1
    ;;
esac
echo "Done."
