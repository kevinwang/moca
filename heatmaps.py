import json

course_ids = ['textretrieval', 'textanalytics']

heatmaps = {}
for course_id in course_ids:
    with open('heatmaps/%s-heatmap.json' % course_id) as jsonfile:
        heatmaps[course_id] = json.load(jsonfile)

def get_heatmap(course_id, lecture_id):
    return heatmaps[course_id][str(lecture_id)]
