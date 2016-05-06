import glob, os
import pysrt
from gensim import corpora, models, similarities
from collections import defaultdict
from pprint import pprint
import nltk.tokenize
from stop_words import get_stop_words
from nltk.stem.porter import PorterStemmer
import csv


tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
p_stemmer = PorterStemmer()
en_stop = get_stop_words('en')
en_stop.append("s")
texts = []
lect_mintexts = {}

for file in os.listdir("textretrieval_srt"):
    if file.endswith(".srt"):
    	current = pysrt.open('textretrieval_srt/'+file)
        t = file.split(' ')
        lecmin = t[0]+t[1]+t[2]
        #print lecmin
    	buckets = []
    	for i in range(len(current)):
    		minute = current[i].start.minutes
    		if len(buckets)>minute:
    			buckets[minute] = buckets[minute]+' '+current[i].text
    		else:
    			buckets.extend(['']*(1+minute-len(buckets)))
    			buckets[minute] = buckets[minute]+current[i].text

    	for j in range(len(buckets)):
            doc = buckets[j]
            raw = doc.lower()
            tokens = tokenizer.tokenize(raw)
            stopped_tokens = [i for i in tokens if not i in en_stop]
            text = [p_stemmer.stem(i) for i in stopped_tokens]
            texts.append(text)
            lect_mintexts[lecmin+'_'+str(j)] = text

#print len(texts)
dictionary = corpora.Dictionary(texts)
print dictionary
corpus = [dictionary.doc2bow(text) for text in texts]
#pprint(lect_mintexts)

ldamodel = models.ldamodel.LdaModel(corpus, num_topics=17, id2word = dictionary, passes=20)
pprint(ldamodel.print_topics(num_topics=17))

minute_topics = {}
for key in lect_mintexts:
    #print key
    current = lect_mintexts[key]
    doc_bow = dictionary.doc2bow(current)
    topic = ldamodel[doc_bow]
    minute_topics[key] = topic
#pprint(minute_topics)

topics_perminute = open('textretrieval_lect_topics.csv','w')
wr = csv.writer(topics_perminute)
aggregate = {}
for minute in minute_topics:
    t = minute.split('_')
    lect = str(t[0])
    m = eval(t[1])
    dist = minute_topics[minute]
    max_prob = 0
    best_topic = 0
    for tup in dist:
        topic,prob = tup
        if prob > max_prob:
            max_prob = prob
            best_topic = topic
    if lect not in aggregate:
        aggregate[lect] = [0]*(m+1)
        aggregate[lect][m] = best_topic
    else:
        if len(aggregate[lect])>m:
            aggregate[lect][m] = best_topic
        else:
            aggregate[lect].extend([0]*(1+m-len(aggregate[lect])))
            aggregate[lect][m] = best_topic

lec_ids = {'1-1':12,'1-2':24,'2-1':26,'2-2':28,'2-3':30,'2-4':32,'2-5':20,'2-6':34,'2-7':36,'2-8':38,'2-9':40,
'3-1':42,'3-2':44,'3-3':46,'3-4':48,'3-5':50,'3-6':52,'3-7':60,'3-8':54,'3-9':56,
'4-1':62,'4-2':68,'4-3':66,'4-4':78,'4-5':80,'4-6':70,'4-7':118,'4-8':74,'4-9':76,'4-10':82,
'5-1':102,'5-2':100,'5-3':98,'5-4':104,'5-5':106,'5-6':96,'5-7':108,'5-8':110,'5-9':94,'5-10':92,'5-11':112,'5-12':90,'5-13':114,'5-14':116,'5-15':88}
for l in aggregate:
    newrow = [str(lec_ids[l])]
    newrow.extend(aggregate[l])
    wr.writerow(newrow)



