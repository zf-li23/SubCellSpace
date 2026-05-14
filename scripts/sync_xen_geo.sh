#!/bin/bash
# Sync Xenium GEO dirs from old cluster paths to new DB paths  
# Maps existing cluster directories to DB entries by matching old dataset ID

DATA=/data3/yangxr002/Xenium
DB=/Share/home/yangxr002/zf-li23/xen_geo_map.txt

echo "Finding Xenium GEO dirs on cluster..."
find $DATA -maxdepth 3 -type d -regex ".*/P1[0-9]+/D1[0-9]+" | while read olddir; do
  did=$(basename "$olddir")
  echo "$did $olddir"
done
