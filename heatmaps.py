import json
import os

from courses import courses

filedir = os.path.dirname(__file__)

heatmaps = {}
for course_id in courses:
    filename = os.path.join(filedir, 'heatmaps/%s-heatmap.json' % course_id)
    with open(filename) as jsonfile:
        heatmaps[course_id] = json.load(jsonfile)

def get_heatmap(course_id, lecture_id):
    return heatmaps[course_id][str(lecture_id)]
