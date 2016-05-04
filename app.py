from flask import Flask, redirect, render_template, abort
from functools import wraps
from sqlalchemy import create_engine, MetaData, Table, select

app = Flask(__name__, static_url_path='')
app.debug = True

course_ids = ['textretrieval', 'textanalytics']
engines = {course_id: create_engine('mysql://root@localhost/' + course_id, echo=True) for course_id in course_ids}
metadata = {course_id: MetaData(engine) for course_id, engine in engines.iteritems()}

def validate_course(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'course_id' in kwargs and kwargs['course_id'] not in course_ids:
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
         .where((lecture_metadata.c.parent_id == -1) & (lecture_metadata.c.deleted == 0))
         .order_by(lecture_metadata.c.title))
    result = connection.execute(s)
    connection.close()

    lectures = [{'id': lecture[0], 'title': lecture[1]} for lecture in result]

    hardest_topics = ['hardest', 'harder', 'hard']
    easiest_topics = ['easiest', 'easier', 'easy']

    return render_template(
            'course.html',
            course_id=course_id,
            hardest_topics=hardest_topics,
            easiest_topics=easiest_topics,
            lectures=lectures)

@app.route('/<course_id>/lecture/<int:lecture_id>')
@validate_course
def route_lecture(course_id, lecture_id):
    connection = engines[course_id].connect()
    lecture_metadata = Table('lecture_metadata', metadata[course_id], autoload=True)
    s = (select([lecture_metadata.c.id, lecture_metadata.c.title])
         .where(lecture_metadata.c.id == lecture_id)
         .limit(1))
    result = list(connection.execute(s))
    connection.close()

    if len(result) == 0:
        abort(404)

    lecture = {'id': result[0][0], 'title': result[0][1]}
    return render_template('lecture.html', lecture=lecture)

if __name__ == '__main__':
    app.run()
