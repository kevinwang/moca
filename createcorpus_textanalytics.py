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

for file in os.listdir("textanalysis_srt"):
    if file.endswith(".srt"):
    	current = pysrt.open('textanalysis_srt/'+file)
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
#pprint(lect_mintexts) #wrong

ldamodel = models.ldamodel.LdaModel(corpus, num_topics=15, id2word = dictionary, passes=20)
pprint(ldamodel.print_topics(num_topics=15))

minute_topics = {}
for key in lect_mintexts:
    #print key
    current = lect_mintexts[key]
    doc_bow = dictionary.doc2bow(current)
    topic = ldamodel[doc_bow]
    minute_topics[key] = topic
#pprint(minute_topics) #wrong

topics_perminute = open('textanalysis_lect_topics.csv','w')
wr = csv.writer(topics_perminute)
aggregate = {}
distinct = {}
for minute in minute_topics:
    t = minute.split('_')
    lect = str(t[0])
    distinct[lect] = 1
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
# print "distinct: "
# print len(distinct)
# print "aggregate: "
# print len(aggregate)
lec_ids = {'1-1':39,'1-2':37,'2-1':41,'2-2':43,'2-3':45,'2-4':47,'2-5':49,'2-6':51,'2-7':53,'2-8':57,'2-9':61,'2-10':63,'2-11':65,'2-12':67,'2-13':69,
'3-1':73,'3-2':75,'3-3':77,'3-4':79,'3-5':81,'3-6':83,'3-7':85,'3-8':87,'3-9':89,'3-10':91,'3-11':93,'3-12':95,'3-13':97,'3-14':99,'3-15':101,'3-16':103,
'4-1':105,'4-2':107,'4-3':109,'4-4':111,'4-5':113,'4-6':115,'4-7':117,'4-8':119,'4-9':121,'4-10':123,'4-11':125,'4-12':127,'4-13':131,
'5-1':135,'5-2':137,'5-3':139,'5-4':141,'5-5':143,'5-6':145,'5-7':147,'5-8':149,'5-9':151,'5-10':153,'5-11':155}
#print len(lec_ids)

for l in aggregate:
    newrow = [str(lec_ids[l])]
    newrow.extend(aggregate[l])
    wr.writerow(newrow)



