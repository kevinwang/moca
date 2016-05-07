#!/usr/bin/env python
"""Import topic distributions and minute-by-minute topic coverage to SQL.

Usage: ./import_topics.py
"""

import ConfigParser
import csv
import os
from sqlalchemy import *
import sys

config = ConfigParser.RawConfigParser()
filedir = os.path.dirname(__file__)
config.read(os.path.join(filedir, '../moca.cfg'))
sys.path.insert(0, os.path.join(filedir, '..'))

from courses import courses
import heatmaps

db_prefix = 'mysql://%s:%s@%s/' % (
        config.get('Database', 'username'),
        config.get('Database', 'password'),
        config.get('Database', 'host'))
engines = {course_id: create_engine(db_prefix + course_id, echo=True) for course_id in courses}
metadata = {course_id: MetaData(engine) for course_id, engine in engines.iteritems()}

# Tables by course id
moca_topics = {}
moca_topic_words = {}
moca_topic_coverage = {}

# Reset `moca_topics` and `moca_topic_words` tables
for course_id in courses:
    moca_topics[course_id] = Table('moca_topics', metadata[course_id],
        Column('id', Integer, primary_key=True, autoincrement=False),
        Column('name', String(100)))

    moca_topic_words[course_id] = Table('moca_topic_words', metadata[course_id],
        Column('topic_id', Integer, ForeignKey('moca_topics.id')),
        Column('word', String(100)),
        Column('phi', Float))

    lecture_metadata = Table('lecture_metadata', metadata[course_id], autoload=True)

    moca_topic_coverage[course_id] = Table('moca_topic_coverage', metadata[course_id],
        Column('lecture_id', Integer, ForeignKey('lecture_metadata.id'), primary_key=True),
        Column('minute', Integer, primary_key=True, autoincrement=False),
        Column('topic_id', Integer, ForeignKey('moca_topics.id')))

    moca_topic_coverage[course_id].drop(engines[course_id], checkfirst=True)
    moca_topic_words[course_id].drop(engines[course_id], checkfirst=True)
    moca_topics[course_id].drop(engines[course_id], checkfirst=True)
    moca_topics[course_id].create(engines[course_id])
    moca_topic_words[course_id].create(engines[course_id])
    moca_topic_coverage[course_id].create(engines[course_id])

topics = {}

with open(os.path.join(filedir, 'topic_TextRetrieval.txt')) as f:
    topics['textretrieval'] = eval(f.read())

with open(os.path.join(filedir, 'topic_TextAnalytics.txt')) as f:
    topics['textanalytics'] = eval(f.read())

for course_id in courses:
    connection = engines[course_id].connect()

    for topic in topics[course_id]:
        topic_id = int(topic[0])
        words = topic[1].split(' + ')
        words = [word.split('*') for word in words]
        words = [(float(word[0]), word[1]) for word in words]

        # Insert topic to `moca_topics`
        topic_ins = moca_topics[course_id].insert().values(
            id=topic_id,
            name=' '.join([words[0][1], words[1][1], words[2][1]]))
        connection.execute(topic_ins)

        # Insert all words to `moca_topic_words`
        for word in words:
            word_ins = moca_topic_words[course_id].insert().values(
                topic_id=topic_id,
                word=word[1],
                phi=word[0])
            connection.execute(word_ins)

    with open(os.path.join(filedir, course_id + '_lect_topics.csv')) as f:
        reader = csv.reader(f)
        for row in reader:
            lecture_id = int(row[0])
            lecture_topics = filter(None, row[1:])
            for minute, topic_id in enumerate(lecture_topics):
                cov_ins = moca_topic_coverage[course_id].insert().values(
                    lecture_id=lecture_id,
                    minute=minute,
                    topic_id=topic_id)
                connection.execute(cov_ins)

    connection.close()
