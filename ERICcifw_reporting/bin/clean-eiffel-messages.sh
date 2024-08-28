#!/bin/bash
# Delete log files versions older than 30 days
find /proj/lciadm100/cifwk/logs/messagebus \
-type f -mtime +30 -exec rm -rf {} \;
