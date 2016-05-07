from flask import Flask, redirect, render_template, abort, Response, \
        stream_with_context
from functools import wraps
import ConfigParser
import os
from pycaption import CaptionConverter, SRTReader, WebVTTWriter, \
        CaptionReadNoCaptions
import requests
from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.sql import func

from courses import courses
import heatmaps

app = Flask(__name__)
app.debug = True

config = ConfigParser.RawConfigParser()
filedir = os.path.dirname(__file__)
config.read(os.path.join(filedir, 'moca.cfg'))

db_prefix = 'mysql://%s:%s@%s/' % (
        config.get('Database', 'username'),
        config.get('Database', 'password'),
        config.get('Database', 'host'))
engines = {course_id: create_engine(db_prefix + course_id, echo=True) for course_id in courses}
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
    ls = (select([lecture_metadata.c.id, lecture_metadata.c.title])
         .where((lecture_metadata.c.parent_id == -1) &
                (lecture_metadata.c.deleted == 0))
         .order_by(lecture_metadata.c.title))
    lectures_result = connection.execute(ls)

    moca_topics = Table('moca_topics', metadata[course_id], autoload=True)
    ts = select([moca_topics]).order_by(moca_topics.c.difficulty.desc())
    topics_result = connection.execute(ts)
    connection.close()

    lectures = [{'id': lecture[0], 'title': lecture[1]} for lecture in lectures_result]

    hardest_topics = [topic for topic in topics_result]
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
    ls = (select([lecture_metadata.c.id, lecture_metadata.c.title, lecture_metadata.c.source_video, lecture_metadata.c.video_id])
         .where((lecture_metadata.c.id == lecture_id) &
                (lecture_metadata.c.parent_id == -1) &
                (lecture_metadata.c.deleted == 0))
         .limit(1))
    lecture_result = list(connection.execute(ls))

    moca_topics = Table('moca_topics', metadata[course_id], autoload=True)
    moca_topic_coverage = Table('moca_topic_coverage', metadata[course_id], autoload=True)
    cs = (select([moca_topic_coverage, moca_topics])
          .select_from(moca_topic_coverage.join(moca_topics))
          .where(moca_topic_coverage.c.lecture_id == lecture_id)
          .order_by(moca_topic_coverage.c.minute))
    coverage_result = [dict(c) for c in connection.execute(cs)]
    connection.close()

    if len(lecture_result) == 0:
        abort(404)

    lecture = lecture_result[0]
    lecture_data = {
        'id': lecture['id'],
        'title': lecture['title'],
        'video_url_webm': 'http://d396qusza40orc.cloudfront.net/' + course_id + '/recoded_videos%2F' + lecture['source_video'].replace('.mp4', '.' + lecture['video_id'] + '.webm'),
        'video_url_mp4': 'http://d396qusza40orc.cloudfront.net/' + course_id + '/recoded_videos%2F' + lecture['source_video'].replace('.mp4', '.' + lecture['video_id'] + '.mp4'),
        'subtitles_url': '/%s/lecture/%d/subtitles' % (course_id, lecture_id),
    }
    return render_template(
            'lecture.html',
            course_id=course_id,
            lecture=lecture_data,
            heatmap=heatmaps.get_heatmap(course_id, lecture_id),
            coverage=coverage_result)

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

@app.route('/<course_id>/topic/<int:topic_id>')
@validate_course
def route_topic(course_id, topic_id):
    connection = engines[course_id].connect()
    moca_topics = Table('moca_topics', metadata[course_id], autoload=True)
    ts = select([moca_topics]).where(moca_topics.c.id == topic_id)
    topic_result = list(connection.execute(ts))

    moca_topic_words = Table('moca_topic_words', metadata[course_id], autoload=True)
    ws = (select([moca_topic_words])
          .where(moca_topic_words.c.topic_id == topic_id)
          .order_by(moca_topic_words.c.phi.desc()))
    words_result = [dict(w) for w in connection.execute(ws)]

    lecture_metadata = Table('lecture_metadata', metadata[course_id], autoload=True)
    moca_topic_coverage = Table('moca_topic_coverage', metadata[course_id], autoload=True)
    ls = (select([lecture_metadata.c.id, lecture_metadata.c.title, func.count().label('num_minutes')])
          .select_from(lecture_metadata.join(moca_topic_coverage))
          .where(moca_topic_coverage.c.topic_id == topic_id)
          .group_by(lecture_metadata.c.id)
          .order_by('num_minutes DESC'))
    lectures_result = [dict(l) for l in connection.execute(ls)]
    connection.close()

    if len(topic_result) == 0:
        abort(404)

    topic = topic_result[0]

    return render_template(
        'topic.html',
        course_id=course_id,
        topic=topic,
        words=words_result,
        lectures=lectures_result)

if __name__ == '__main__':
    app.run()
