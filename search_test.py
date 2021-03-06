import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

import django
django.setup()

from papers.models import Article
from papers.models import Tag
from papers.models import Affiliation
from papers.models import Author
from datetime import date

import re
import time
import string

from django.db.models import Q

stopwords='''a, about, again, all, almost, also, although, always, among, an, and, another, any, are, as, at,
be, because, been, before, being, between, both, but, by,
can, could,
did, do, does, done, due, during,
each, either, enough, especially, etc,
for, found, from, further,
had, has, have, having, here, how, however,
i, if, in, into, is, it, its, itself,
just,
kg, km,
made, mainly, make, may, mg, might, ml, mm, most, mostly, must,
nearly, neither, no, nor,
obtained, of, often, on, our, overall,
perhaps, pmid,
quite,
rather, really, regarding,
seem, seen, several, should, show, showed, shown, shows, significantly, since, so, some, such,
than, that, the, their, theirs, them, then, there, therefore, these, they, this, those, through, thus, to,
upon, use, used, using,
various, very,
was, we, were, what, when, which, while, with, within, without, would'''

stopwords=[i.strip() for i in stopwords.split(',')]

mypunctuation='!#"$%&()*+,./:;<=>?@\\^_`{|}~'

mytable = string.maketrans(mypunctuation,' '*len(mypunctuation))

##instead of deleting the characters convert to spaces unless double quoted, merge afterwards
	

def normalize_query(query_string):
    normspace=re.compile(r'\s{2,}').sub
    findterms=re.compile(r'"([^"]+)"|(\S+)').findall
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] 

def tiab_query(query_string):
    query = None        
    terms = query_string
    for term in terms:
        or_query = None
        for field_name in ['title','abstract']:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query


#example
name_test=[['John','Smith'],[['first','full'],['last','full']]]

##def au_query(names):
##    and_query = None
##    for index, name in enumerate(names[0]):
##        if names[1][index][1]=='full':
##            q = Q(**{"authors__%s__iexact" % names[1][index][0]: name})
##        else:
##            q = Q(**{"authors__%s__istartswith" % names[1][index][0]: name})
##        if and_query is None:
##            and_query = q
##        else:
##            and_query = and_query & q
##    return and_query


def au_query(names):
    and_query = None
    for index, name in enumerate(names[0]):
        if names[1][index][1]=='full':
            q = Q(**{"%s__iexact" % names[1][index][0]: name})
        else:
            q = Q(**{"%s__istartswith" % names[1][index][0]: name})
        if and_query is None:
            and_query = q
        else:
            and_query = and_query & q
    return and_query







def super_query(all_terms):
    query=None
    for i in all_terms['names']:
        q=au_query(i)
        if query is None:
            query=q
        else:
            query=query & q
    if all_terms['terms']!=[]:
        q=tiab_query(all_terms['terms'])
        if query is None:
            query=q
        else:
            query=query & q
    return query

def perform_query(all_terms):
    qs=[]
    if all_terms['terms']!=[]:
        q=tiab_query(all_terms['terms'])
        qs=Article.objects.filter(q)
        for i in all_terms['names']:
            qs=qs.filter(au_query(i))
    else:
        if all_terms['names']!=[]:
            qs=Article.objects.filter(au_query(all_terms['names'][0]))
            for i in all_terms['names'][1:]:
                qs=qs.filter(au_query(i))
    return qs





##for each author create a list that contains as much info as possible
##[the name (first),],[full or abb]]

#example
[['John','Smith'],[['first','full'],['last','full']]]


##need a function which will group authors together, and other names together

raw='eisen coil'.lower()

rawstring=normalize_query(raw)

finalstring=[]
for i in rawstring:
    if len(i.split())>1:
        finalstring.append(i)
    else:
        if string.translate(i,mytable)==i:
            finalstring.append(i)
        else:
            finalstring+=normalize_query(string.translate(i,mytable))

all_terms={'names':[],'terms':[]}

##not removing punctuation from quoted strings or stopwords



def parsing_query(mystring,all_terms):
    while mystring:
        query=mystring[0]
        if len(query.split())==1:
            if query in name_last:
                if len(mystring)!=1:
                    query_plus_1=mystring[1]
                    if len(query_plus_1.split())==1:
                        if len(query_plus_1)>2:
                            if query_plus_1 in name_first:
                                ##check if query is e.g. wong julia, could still be wong j, or wong julia s
                                if query in name_first[query_plus_1][0]:
                                    ##confirmed first name and last name could match, check for middle abbreviation
                                    if len(mystring)!=2:
                                        query_plus_2=mystring[2]
                                        if len(query_plus_2.split())==1:
                                            ##check abbreviation, limit length
                                            if len(query_plus_2)<=2:
                                                if query_plus_2 in name_first[query_plus_1][1]:
                                                    all_terms['names']=all_terms.get('names',[])+[[[query_plus_1,query_plus_2,query],[['first','full'],['middle',''],['last','full']]]]
                                                    return parsing_query(mystring[3:],all_terms)
                                                else:
                                                    all_terms['names']=all_terms.get('names',[])+[[[query_plus_1,query],[['first','full'],['last','full']]]]
                                                    return parsing_query(mystring[2:],all_terms)
                                            else:
                                                all_terms['names']=all_terms.get('names',[])+[[[query_plus_1,query],[['first','full'],['last','full']]]]
                                                return parsing_query(mystring[2:],all_terms)
                                        else:
                                            ##handle quoted string here, if there are two words can't be abbreviation
                                            all_terms['names']=all_terms.get('names',[])+[[[query_plus_1,query],[['first','full'],['last','full']]]]
                                            return parsing_query(mystring[2:],all_terms)
                                    else:
                                        all_terms['names']=all_terms.get('names',[])+[[[query_plus_1,query],[['first','full'],['last','full']]]]
                                        return parsing_query(mystring[2:],all_terms)
                                else:
                                    all_terms['names']=all_terms.get('names',[])+[[[query],[['last','full']]]]
                                    return parsing_query(mystring[1:],all_terms)
                            else:
                                all_terms['names']=all_terms.get('names',[])+[[[query],[['last','full']]]]
                                return parsing_query(mystring[1:],all_terms)
                        else:
                            #could still be wong j or wong js
                            if len(query_plus_1)==1:
                                #check for first name abbreviation
                                if query_plus_1 in name_last[query][0]:
                                    all_terms['names']=all_terms.get('names',[])+[[[query_plus_1,query],[['first',''],['last','full']]]]
                                    return parsing_query(mystring[2:],all_terms)
                                else:
                                    all_terms['names']=all_terms.get('names',[])+[[[query],[['last','full']]]]
                                    return parsing_query(mystring[1:],all_terms)
                            elif len(query_plus_1)==2:
                                #check for first name middle name abbreviation
                                ##make a list of possible middle abbreviations
                                middle_abb=[middle for middle,first in zip(name_last[query][1],name_last[query][0]) if first==query_plus_1[0] and middle!='']
                                if query_plus_1[1] in middle_abb:
                                    all_terms['names']=all_terms.get('names',[])+[[[query_plus_1[0],query,query_plus_1[1]],[['first',''],['last','full'],['middle','']]]]
                                    return parsing_query(mystring[2:],all_terms)
                                else:
                                    all_terms['names']=all_terms.get('names',[])+[[[query],[['last','full']]]]
                                    return parsing_query(mystring[1:],all_terms)
                    else:
                        #handle quoted here
                        ##treating this as a new search term
                        all_terms['names']=all_terms.get('names',[])+[[[query],[['last','full']]]]
                        return parsing_query(mystring[1:],all_terms)
                else:
                    all_terms['names']=all_terms.get('names',[])+[[[query],[['last','full']]]]
                    return parsing_query(mystring[1:],all_terms)
            elif query in name_first:
                if len(mystring)!=1:
                    query_plus_1=mystring[1]
                    if len(query_plus_1.split())==1:
                        if query_plus_1 in name_first[query][0]:
                            ##check if query is e.g. julia wong, if so return name
                            if query_plus_1 in name_first[query][0]:
                                all_terms['names']=all_terms.get('names',[])+[[[query,query_plus_1],[['first','full'],['last','full']]]]
                                return parsing_query(mystring[2:],all_terms)
                            else:
                                all_terms['names']=all_terms.get('names',[])+[[[query],[['first','full']]]]
                                return parsing_query(mystring[1:],all_terms)
                        else:
                            ##check for initial, e.g. julia s wong
                            if len(query_plus_1)<=2 and len(mystring)!=2:
                                query_plus_2=mystring[2]
                                if len(query_plus_2.split())==1:
                                    if query_plus_2 in name_first[query][0]:
                                        #check if the middle initial is in the correct place in the list
                                        #need to get a list of the first middle initial of each matching last name first name combo if middle exists
                                        middle_list=[middle[0] for last,middle in zip(name_first[query][0],name_first[query][1]) if last==query_plus_2 and middle!='']
                                        if query_plus_1[0] in middle_list:
                                            all_terms['names']=all_terms.get('names',[])+[[[query,query_plus_1,query_plus_2],[['first','full'],['middle',''],['last','full']]]]
                                            return parsing_query(mystring[3:],all_terms)
                                        else:
                                            all_terms['names']=all_terms.get('names',[])+[[[query,query_plus_2],[['first','full'],['last','full']]]]
                                            ##the middle initial was not found, but still allowing search to proceed
                                            all_terms['unknown']=all_terms.get('unknown',[])+[query_plus_1]
                                            return parsing_query(mystring[3:],all_terms)
                                    else:
                                        all_terms['names']=all_terms.get('names',[])+[[[query],[['first','full']]]]
                                        return parsing_query(mystring[1:],all_terms)        
                                else:
                                    #handle quoted here
                                    #last name is not allowed to be two words, return first name
                                    all_terms['names']=all_terms.get('names',[])+[[[query],[['first','full']]]]
                                    return parsing_query(mystring[1:],all_terms)
                            else:
                                all_terms['names']=all_terms.get('names',[])+[[[query],[['first','full']]]]
                                return parsing_query(mystring[1:],all_terms)           
                    else:
                        #handle quoted here
                        #use quoted strings to denote a new search term, stop name search here, return first
                        all_terms['names']=all_terms.get('names',[])+[[[query],[['first','full']]]]
                        return parsing_query(mystring[1:],all_terms)
                else:
                    all_terms['names']=all_terms.get('names',[])+[[[query],[['first','full']]]]
                    return parsing_query(mystring[1:],all_terms)
            else:
                if query not in stopwords:
                    all_terms['terms']=all_terms.get('terms',[])+[query]
                    return parsing_query(mystring[1:],all_terms)
                else:
                    return parsing_query(mystring[1:],all_terms)
        else:
            #handle quoted strings here
            ##quoted strings will be used to denote phrases instead of authors
            all_terms['terms']=all_terms.get('terms',[])+[query]
            return parsing_query(mystring[1:],all_terms)
    return all_terms
                
            




##my_Q=super_query(parsing_query(finalstring,all_terms))
##
##print my_Q
import datetime

#do an author test

q=au_query([['Jordan','Anaya'],[['first','full'],['last','full']]])
q=au_query([['Church'],[['last','full']]])


all_terms={'names':[[['Jordan','Anaya'],[['first','full'],['last','full']]]],'terms':[]}
for i in range(10):
    start=time.time()
##    qs1=Article.objects.filter(tags__name="Cancer Biology").all().order_by('-pub_date')
##    qs2=Tag.objects.get(name="Bioinformatics").article_set.all().filter(pub_date__gte=datetime.date(2014,1,1))

##    qs=Article.objects.filter(q).order_by('-pub_date')
##    qs=perform_query(all_terms).order_by('-pub_date')
    qs=Author.objects.filter(q)
    #get articles of each queryset
    qs2=qs[0].article_set.all()
    for a in qs[1:]:
        qs2=qs2 | a.article_set.all()
    qs2.order_by('-pub_date')
    result=[(i.pub_date,i.link) for i in qs2]
    end=time.time()
    print end-start


##start=time.time()
##qs=perform_query(parsing_query(finalstring,all_terms))
##qs=Article.objects.filter(abstract__icontains="a")
##len(qs)
##authors=Article.objects.all().values().prefetch_related('authors')
##print len([i.authors for i in authors])
##end=time.time()
##print end-start


















