from flask import Flask, redirect, render_template, url_for

app = Flask(__name__, static_url_path='')
app.debug = True

@app.route('/')
def home():
    return redirect('/course/textretrieval-001')

@app.route('/coursestest')
def coursetest():
    return render_template('specific.html')


@app.route('/course/<course_id>')
def course(course_id):
    hardest_topics = ['hardest', 'harder', 'hard']
    easiest_topics = ['easiest', 'easier', 'easy']
    videos = ['1.1', '1.2', '1.3']
    return render_template(
            'course.html',
            course_id=course_id,
            hardest_topics=hardest_topics,
            easiest_topics=easiest_topics,
            videos=videos)

if __name__ == '__main__':
    app.run()
