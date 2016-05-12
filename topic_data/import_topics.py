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
engines = {course_id: create_engine(db_prefix + course_id, echo=True, pool_recycle=3600) for course_id in courses}
metadata = {course_id: MetaData(engine) for course_id, engine in engines.iteritems()}

# Tables by course id
moca_topics = {}
moca_topic_words = {}
moca_topic_coverage = {}

# Human-assigned topic names
rectified_topics = {
    'textretrieval': {
        0: 'document relevance',
        1: 'search engine',
        2: 'feedback relevance',
        3: 'user',
        6: 'natural language',
        9: 'vector space model',
        10: 'recommender systems',
        11: 'indexing',
        12: 'crawling framework',
        13: 'precision/recall metrics',
        14: 'human-in-the-loop support',
        15: 'PageRank',
        16: 'MapReduce',
    },
    'textanalytics': {
        0: 'topic model',
        1: 'information entropy',
        2: 'retrieval model',
        3: 'generative',
        4: 'probabilistic model',
        7: 'classification',
        14: 'paradigmatic/syntagmatic relations',
    },
}

# Reset `moca_topics` and `moca_topic_words` tables
for course_id in courses:
    moca_topics[course_id] = Table('moca_topics', metadata[course_id],
        Column('id', Integer, primary_key=True, autoincrement=False),
        Column('name', String(100)),
        Column('difficulty', Float))

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

for course_id in courses:
    connection = engines[course_id].connect()

    with open(os.path.join(filedir, course_id + '_topics.txt')) as f:
        topics = eval(f.read())

    # Import topics and word distributions
    for topic in topics:
        topic_id = int(topic[0])
        words = topic[1].split(' + ')
        words = [word.split('*') for word in words]
        words = [(float(word[0]), word[1]) for word in words]

        if topic_id in rectified_topics[course_id]:
            name = rectified_topics[course_id][topic_id]
        else:
            name = ' '.join([words[0][1], words[1][1], words[2][1]])

        # Insert topic to `moca_topics`
        topic_ins = moca_topics[course_id].insert().values(
            id=topic_id,
            name=name)
        connection.execute(topic_ins)

        # Insert all words to `moca_topic_words`
        for word in words:
            word_ins = moca_topic_words[course_id].insert().values(
                topic_id=topic_id,
                word=word[1],
                phi=word[0])
            connection.execute(word_ins)

    # Import topic coverage by lecture x minute while simultaneously
    # calculating topic difficulties
    topic_num_events = [0] * len(topics)
    topic_num_minutes = [0] * len(topics)
    with open(os.path.join(filedir, course_id + '_lect_topics.csv')) as f:
        reader = csv.reader(f)
        for row in reader:
            lecture_id = int(row[0])
            lecture_topics = map(int, filter(None, row[1:]))
            heatmap = heatmaps.get_heatmap(course_id, lecture_id)
            for minute, topic_id in enumerate(lecture_topics):
                cov_ins = moca_topic_coverage[course_id].insert().values(
                    lecture_id=lecture_id,
                    minute=minute,
                    topic_id=topic_id)
                connection.execute(cov_ins)

                try:
                    topic_num_events[topic_id] += heatmap[minute]
                    topic_num_minutes[topic_id] += 1
                except IndexError:
                    continue

    topic_difficulties = [float(e) / m for e, m in zip(topic_num_events, topic_num_minutes)]

    for topic_id, difficulty in enumerate(topic_difficulties):
        stmt = (moca_topics[course_id].update()
                .where(moca_topics[course_id].c.id == topic_id)
                .values(difficulty=difficulty))
        connection.execute(stmt)

    connection.close()
