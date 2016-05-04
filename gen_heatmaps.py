#!/usr/bin/env python
"""Generate play/pause/seeked event heatmaps from raw Coursera event data.

Usage: grep 'user\.video\.lecture\.action.*\(play\|pause\|seeked\)' *ClickStreamData_NonPII.csv | cut -d, -f3,10,13 | sed -E 's/https:\/\/class.coursera.org\/.*\/lecture\/view\?lecture_id\=([0-9]+).*$/\1/' | awk 'BEGIN{FS=OFS=","} { print $3,$1,$2 }' | ./gen_heatmaps.py
"""

from collections import defaultdict, Counter
import csv
import json
import sys

lectures = defaultdict(Counter)
lecture_mins = defaultdict(int)

reader = csv.reader(sys.stdin)
for row in reader:
    lecture_id = int(row[0])
    try:
        if float(row[1]) > 0:
            minute = int(float(row[1])) / 60
            lectures[lecture_id][minute] += 1
            lecture_mins[lecture_id] = max(lecture_mins[lecture_id], minute + 1)
    except ValueError:
        continue

heatmaps = {}
for lecture_id, counts in lectures.iteritems():
    heatmaps[lecture_id] = [0] * lecture_mins[lecture_id]
    for minute in sorted(lectures[lecture_id]):
        heatmaps[lecture_id][minute] = lectures[lecture_id][minute]

print json.dumps(heatmaps)
