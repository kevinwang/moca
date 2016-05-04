from flask import Flask, redirect, render_template, abort, Response, \
        stream_with_context
from functools import wraps
from pycaption import CaptionConverter, SRTReader, WebVTTWriter, \
        CaptionReadNoCaptions
import requests
from sqlalchemy import create_engine, MetaData, Table, select

from courses import courses
import heatmaps

app = Flask(__name__)
app.debug = True

engines = {course_id: create_engine('mysql://root@localhost/' + course_id, echo=True) for course_id in courses}
metadata = {course_id: MetaData(engine) for course_id, engine in engines.iteritems()}

def validate_course(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'course_id' in kwargs and kwargs['course_id'] not in courses:
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def route_home():
    return render_template('home.html')

@app.route('/coursestest')
def route_coursetest():
    return render_template('specific.html')


@app.route('/<course_id>')
@validate_course
def route_course(course_id):
    connection = engines[course_id].connect()
    lecture_metadata = Table('lecture_metadata', metadata[course_id], autoload=True)
    # TODO: Sort properly by x.y lecture number so 1.10 doesn't come before 1.2
    s = (select([lecture_metadata.c.id, lecture_metadata.c.title])
         .where((lecture_metadata.c.parent_id == -1) &
                (lecture_metadata.c.deleted == 0))
         .order_by(lecture_metadata.c.title))
    result = connection.execute(s)
    connection.close()

    lectures = [{'id': lecture[0], 'title': lecture[1]} for lecture in result]

    hardest_topics = ['hardest', 'harder', 'hard']
    easiest_topics = ['easiest', 'easier', 'easy']

    return render_template(
            'course.html',
            course_name=courses[course_id],
            course_id=course_id,
            hardest_topics=hardest_topics,
            easiest_topics=easiest_topics,
            lectures=lectures)

@app.route('/<course_id>/lecture/<int:lecture_id>')
@validate_course
def route_lecture(course_id, lecture_id):
    connection = engines[course_id].connect()
    lecture_metadata = Table('lecture_metadata', metadata[course_id], autoload=True)
    s = (select([lecture_metadata.c.id, lecture_metadata.c.title, lecture_metadata.c.source_video, lecture_metadata.c.video_id])
         .where((lecture_metadata.c.id == lecture_id) &
                (lecture_metadata.c.parent_id == -1) &
                (lecture_metadata.c.deleted == 0))
         .limit(1))
    result = list(connection.execute(s))
    connection.close()

    if len(result) == 0:
        abort(404)

    result = result[0]
    lecture = {
        'id': result[0],
        'title': result[1],
        'video_url_webm': 'http://d396qusza40orc.cloudfront.net/' + course_id + '/recoded_videos%2F' + result[2].replace('.mp4', '.' + result[3] + '.webm'),
        'video_url_mp4': 'http://d396qusza40orc.cloudfront.net/' + course_id + '/recoded_videos%2F' + result[2].replace('.mp4', '.' + result[3] + '.mp4'),
        'subtitles_url': '/%s/lecture/%d/subtitles' % (course_id, lecture_id),
    }
    return render_template(
            'lecture.html',
            course_id=course_id,
            lecture=lecture,
            heatmap=heatmaps.get_heatmap(course_id, lecture_id))

@app.route('/<course_id>/lecture/<int:lecture_id>/subtitles')
@validate_course
def route_subtitles(course_id, lecture_id):
    subtitles_url = (
            'https://class.coursera.org/%s-001/lecture/subtitles?q=%d_en' %
            (course_id, lecture_id))
    r = requests.get(subtitles_url)
    try:
        converter = CaptionConverter()
        converter.read(r.text, SRTReader())
        subtitles = converter.write(WebVTTWriter())
    except CaptionReadNoCaptions:
        subtitles = ''
    return Response(subtitles, content_type='text/vtt')

if __name__ == '__main__':
    app.run()
