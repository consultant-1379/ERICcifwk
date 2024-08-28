#!/bin/bash

# Crontab command
# 0 0 * * 1 bash -c "ERICcifwk/ERICcifw_reporting/bin/cifwk-cleanup-old-versions.sh"

cd /proj/lciadm100/cifwk
echo "Searching for old cifwk verions to remove..."
# Delete cifwk versions older than 30 days, excluding the current and new version
find -maxdepth 1 -type d ! -path "./$1" ! -path "./$2" -regextype posix-extended \
-regex '^\./[0-9]+\.[0-9]+\.[0-9]+$' -mtime +30 -exec rm -rf {} \; -print

echo "Finished Cleaning Up Old Versions in cifwk"
