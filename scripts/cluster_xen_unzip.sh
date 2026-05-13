#!/bin/bash
set -e
OK=0
FAIL=0

echo "Will extract 39 TAR files (serial, one at a time)"

echo "[D1086] GSE161369_RAW.tar -> /data3/yangxr002/Xenium/P1047/D1086"
mkdir -p "/data3/yangxr002/Xenium/P1047/D1086"
if [ -f "/data3/yangxr002/Xenium/GSE161369_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE161369_RAW.tar" -C "/data3/yangxr002/Xenium/P1047/D1086" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE161369_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1087] GSE231998_RAW.tar -> /data3/yangxr002/Xenium/P1048/D1087"
mkdir -p "/data3/yangxr002/Xenium/P1048/D1087"
if [ -f "/data3/yangxr002/Xenium/GSE231998_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE231998_RAW.tar" -C "/data3/yangxr002/Xenium/P1048/D1087" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE231998_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1088] GSE243168_RAW.tar -> /data3/yangxr002/Xenium/P1049/D1088"
mkdir -p "/data3/yangxr002/Xenium/P1049/D1088"
if [ -f "/data3/yangxr002/Xenium/GSE243168_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE243168_RAW.tar" -C "/data3/yangxr002/Xenium/P1049/D1088" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE243168_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1090] GSE250346_RAW.tar -> /data3/yangxr002/Xenium/P1051/D1090"
mkdir -p "/data3/yangxr002/Xenium/P1051/D1090"
if [ -f "/data3/yangxr002/Xenium/GSE250346_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE250346_RAW.tar" -C "/data3/yangxr002/Xenium/P1051/D1090" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE250346_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1091] GSE251937_RAW.tar -> /data3/yangxr002/Xenium/P1052/D1091"
mkdir -p "/data3/yangxr002/Xenium/P1052/D1091"
if [ -f "/data3/yangxr002/Xenium/GSE251937_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE251937_RAW.tar" -C "/data3/yangxr002/Xenium/P1052/D1091" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE251937_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1092] GSE251938_RAW.tar -> /data3/yangxr002/Xenium/P1053/D1092"
mkdir -p "/data3/yangxr002/Xenium/P1053/D1092"
if [ -f "/data3/yangxr002/Xenium/GSE251938_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE251938_RAW.tar" -C "/data3/yangxr002/Xenium/P1053/D1092" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE251938_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1094] GSE263498_RAW.tar -> /data3/yangxr002/Xenium/P1055/D1094"
mkdir -p "/data3/yangxr002/Xenium/P1055/D1094"
if [ -f "/data3/yangxr002/Xenium/GSE263498_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE263498_RAW.tar" -C "/data3/yangxr002/Xenium/P1055/D1094" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE263498_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1095] GSE264334_RAW.tar -> /data3/yangxr002/Xenium/P1056/D1095"
mkdir -p "/data3/yangxr002/Xenium/P1056/D1095"
if [ -f "/data3/yangxr002/Xenium/GSE264334_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE264334_RAW.tar" -C "/data3/yangxr002/Xenium/P1056/D1095" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE264334_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1097] GSE267680_RAW.tar -> /data3/yangxr002/Xenium/P1058/D1097"
mkdir -p "/data3/yangxr002/Xenium/P1058/D1097"
if [ -f "/data3/yangxr002/Xenium/GSE267680_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE267680_RAW.tar" -C "/data3/yangxr002/Xenium/P1058/D1097" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE267680_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1098] GSE269354_RAW.tar -> /data3/yangxr002/Xenium/P1059/D1098"
mkdir -p "/data3/yangxr002/Xenium/P1059/D1098"
if [ -f "/data3/yangxr002/Xenium/GSE269354_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE269354_RAW.tar" -C "/data3/yangxr002/Xenium/P1059/D1098" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE269354_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1099] GSE270437_RAW.tar -> /data3/yangxr002/Xenium/P1060/D1099"
mkdir -p "/data3/yangxr002/Xenium/P1060/D1099"
if [ -f "/data3/yangxr002/Xenium/GSE270437_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE270437_RAW.tar" -C "/data3/yangxr002/Xenium/P1060/D1099" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE270437_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1101] GSE273557_RAW.tar -> /data3/yangxr002/Xenium/P1062/D1101"
mkdir -p "/data3/yangxr002/Xenium/P1062/D1101"
if [ -f "/data3/yangxr002/Xenium/GSE273557_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE273557_RAW.tar" -C "/data3/yangxr002/Xenium/P1062/D1101" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE273557_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1106] GSE278969_RAW.tar -> /data3/yangxr002/Xenium/P1067/D1106"
mkdir -p "/data3/yangxr002/Xenium/P1067/D1106"
if [ -f "/data3/yangxr002/Xenium/GSE278969_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE278969_RAW.tar" -C "/data3/yangxr002/Xenium/P1067/D1106" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE278969_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1114] GSE283832_RAW.tar -> /data3/yangxr002/Xenium/P1075/D1114"
mkdir -p "/data3/yangxr002/Xenium/P1075/D1114"
if [ -f "/data3/yangxr002/Xenium/GSE283832_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE283832_RAW.tar" -C "/data3/yangxr002/Xenium/P1075/D1114" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE283832_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1115] GSE283843_RAW.tar -> /data3/yangxr002/Xenium/P1076/D1115"
mkdir -p "/data3/yangxr002/Xenium/P1076/D1115"
if [ -f "/data3/yangxr002/Xenium/GSE283843_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE283843_RAW.tar" -C "/data3/yangxr002/Xenium/P1076/D1115" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE283843_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1116] GSE285984_RAW.tar -> /data3/yangxr002/Xenium/P1077/D1116"
mkdir -p "/data3/yangxr002/Xenium/P1077/D1116"
if [ -f "/data3/yangxr002/Xenium/GSE285984_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE285984_RAW.tar" -C "/data3/yangxr002/Xenium/P1077/D1116" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE285984_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1118] GSE286422_RAW.tar -> /data3/yangxr002/Xenium/P1079/D1118"
mkdir -p "/data3/yangxr002/Xenium/P1079/D1118"
if [ -f "/data3/yangxr002/Xenium/GSE286422_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE286422_RAW.tar" -C "/data3/yangxr002/Xenium/P1079/D1118" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE286422_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1123] GSE291246_RAW.tar -> /data3/yangxr002/Xenium/P1084/D1123"
mkdir -p "/data3/yangxr002/Xenium/P1084/D1123"
if [ -f "/data3/yangxr002/Xenium/GSE291246_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE291246_RAW.tar" -C "/data3/yangxr002/Xenium/P1084/D1123" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE291246_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1127] GSE293759_RAW.tar -> /data3/yangxr002/Xenium/P1088/D1127"
mkdir -p "/data3/yangxr002/Xenium/P1088/D1127"
if [ -f "/data3/yangxr002/Xenium/GSE293759_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE293759_RAW.tar" -C "/data3/yangxr002/Xenium/P1088/D1127" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE293759_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1129] GSE293970_RAW.tar -> /data3/yangxr002/Xenium/P1090/D1129"
mkdir -p "/data3/yangxr002/Xenium/P1090/D1129"
if [ -f "/data3/yangxr002/Xenium/GSE293970_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE293970_RAW.tar" -C "/data3/yangxr002/Xenium/P1090/D1129" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE293970_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1130] GSE293972_RAW.tar -> /data3/yangxr002/Xenium/P1091/D1130"
mkdir -p "/data3/yangxr002/Xenium/P1091/D1130"
if [ -f "/data3/yangxr002/Xenium/GSE293972_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE293972_RAW.tar" -C "/data3/yangxr002/Xenium/P1091/D1130" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE293972_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1141] GSE300007_RAW.tar -> /data3/yangxr002/Xenium/P1102/D1141"
mkdir -p "/data3/yangxr002/Xenium/P1102/D1141"
if [ -f "/data3/yangxr002/Xenium/GSE300007_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE300007_RAW.tar" -C "/data3/yangxr002/Xenium/P1102/D1141" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE300007_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1158] GSE308699_RAW.tar -> /data3/yangxr002/Xenium/P1119/D1158"
mkdir -p "/data3/yangxr002/Xenium/P1119/D1158"
if [ -f "/data3/yangxr002/Xenium/GSE308699_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE308699_RAW.tar" -C "/data3/yangxr002/Xenium/P1119/D1158" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE308699_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1166] GSE313662_RAW.tar -> /data3/yangxr002/Xenium/P1127/D1166"
mkdir -p "/data3/yangxr002/Xenium/P1127/D1166"
if [ -f "/data3/yangxr002/Xenium/GSE313662_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE313662_RAW.tar" -C "/data3/yangxr002/Xenium/P1127/D1166" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE313662_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1168] GSE315246_RAW.tar -> /data3/yangxr002/Xenium/P1129/D1168"
mkdir -p "/data3/yangxr002/Xenium/P1129/D1168"
if [ -f "/data3/yangxr002/Xenium/GSE315246_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE315246_RAW.tar" -C "/data3/yangxr002/Xenium/P1129/D1168" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE315246_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1175] GSE322974_RAW.tar -> /data3/yangxr002/Xenium/P1136/D1175"
mkdir -p "/data3/yangxr002/Xenium/P1136/D1175"
if [ -f "/data3/yangxr002/Xenium/GSE322974_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE322974_RAW.tar" -C "/data3/yangxr002/Xenium/P1136/D1175" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE322974_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1181] GSE326837_RAW.tar -> /data3/yangxr002/Xenium/P1142/D1181"
mkdir -p "/data3/yangxr002/Xenium/P1142/D1181"
if [ -f "/data3/yangxr002/Xenium/GSE326837_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE326837_RAW.tar" -C "/data3/yangxr002/Xenium/P1142/D1181" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE326837_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1197] GSE277463_RAW.tar -> /data3/yangxr002/Xenium/P1158/D1197"
mkdir -p "/data3/yangxr002/Xenium/P1158/D1197"
if [ -f "/data3/yangxr002/Xenium/GSE277463_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE277463_RAW.tar" -C "/data3/yangxr002/Xenium/P1158/D1197" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE277463_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1208] GSE284741_RAW.tar -> /data3/yangxr002/Xenium/P1168/D1208"
mkdir -p "/data3/yangxr002/Xenium/P1168/D1208"
if [ -f "/data3/yangxr002/Xenium/GSE284741_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE284741_RAW.tar" -C "/data3/yangxr002/Xenium/P1168/D1208" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE284741_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1215] GSE286129_RAW.tar -> /data3/yangxr002/Xenium/P1175/D1215"
mkdir -p "/data3/yangxr002/Xenium/P1175/D1215"
if [ -f "/data3/yangxr002/Xenium/GSE286129_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE286129_RAW.tar" -C "/data3/yangxr002/Xenium/P1175/D1215" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE286129_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1218] GSE289263_RAW.tar -> /data3/yangxr002/Xenium/P1178/D1218"
mkdir -p "/data3/yangxr002/Xenium/P1178/D1218"
if [ -f "/data3/yangxr002/Xenium/GSE289263_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE289263_RAW.tar" -C "/data3/yangxr002/Xenium/P1178/D1218" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE289263_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1233] GSE299195_RAW.tar -> /data3/yangxr002/Xenium/P1192/D1233"
mkdir -p "/data3/yangxr002/Xenium/P1192/D1233"
if [ -f "/data3/yangxr002/Xenium/GSE299195_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE299195_RAW.tar" -C "/data3/yangxr002/Xenium/P1192/D1233" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE299195_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1241] GSE302473_RAW.tar -> /data3/yangxr002/Xenium/P1198/D1241"
mkdir -p "/data3/yangxr002/Xenium/P1198/D1241"
if [ -f "/data3/yangxr002/Xenium/GSE302473_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE302473_RAW.tar" -C "/data3/yangxr002/Xenium/P1198/D1241" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE302473_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1248] GSE309522_RAW.tar -> /data3/yangxr002/Xenium/P1205/D1248"
mkdir -p "/data3/yangxr002/Xenium/P1205/D1248"
if [ -f "/data3/yangxr002/Xenium/GSE309522_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE309522_RAW.tar" -C "/data3/yangxr002/Xenium/P1205/D1248" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE309522_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1250] GSE310658_RAW.tar -> /data3/yangxr002/Xenium/P1207/D1250"
mkdir -p "/data3/yangxr002/Xenium/P1207/D1250"
if [ -f "/data3/yangxr002/Xenium/GSE310658_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE310658_RAW.tar" -C "/data3/yangxr002/Xenium/P1207/D1250" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE310658_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1259] GSE316666_RAW.tar -> /data3/yangxr002/Xenium/P1215/D1259"
mkdir -p "/data3/yangxr002/Xenium/P1215/D1259"
if [ -f "/data3/yangxr002/Xenium/GSE316666_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE316666_RAW.tar" -C "/data3/yangxr002/Xenium/P1215/D1259" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE316666_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1264] GSE320403_RAW.tar -> /data3/yangxr002/Xenium/P1220/D1264"
mkdir -p "/data3/yangxr002/Xenium/P1220/D1264"
if [ -f "/data3/yangxr002/Xenium/GSE320403_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE320403_RAW.tar" -C "/data3/yangxr002/Xenium/P1220/D1264" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE320403_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1268] GSE328169_RAW.tar -> /data3/yangxr002/Xenium/P1224/D1268"
mkdir -p "/data3/yangxr002/Xenium/P1224/D1268"
if [ -f "/data3/yangxr002/Xenium/GSE328169_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE328169_RAW.tar" -C "/data3/yangxr002/Xenium/P1224/D1268" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE328169_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "[D1270] GSE329229_RAW.tar -> /data3/yangxr002/Xenium/P1226/D1270"
mkdir -p "/data3/yangxr002/Xenium/P1226/D1270"
if [ -f "/data3/yangxr002/Xenium/GSE329229_RAW.tar" ]; then
  tar -xf "/data3/yangxr002/Xenium/GSE329229_RAW.tar" -C "/data3/yangxr002/Xenium/P1226/D1270" 2>/dev/null && OK=$((OK+1)) || { echo "  FAILED"; FAIL=$((FAIL+1)); }
else
  echo "  MISSING TAR: /data3/yangxr002/Xenium/GSE329229_RAW.tar"
  FAIL=$((FAIL+1))
fi

echo "Done. OK=$OK FAIL=$FAIL"
