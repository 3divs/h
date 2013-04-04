import json
import urllib2
import BeautifulSoup
from urlparse import urlparse
 
import time
from dateutil.parser import parse
from datetime import datetime
from dateutil.tz import tzutc
from math import floor
from itertools import chain

import types
import logging
log = logging.getLogger(__name__)


class DisplayerTemplate(object):
    def __init__(self, annotation, replies = [], original = None):
        self._annotation = annotation
        self._replies = replies
        self._original = original
       
    def _url_values(self):
        #Getting the title of the uri.
        #hdrs magic is needed because urllib2 is forbidden to use with default settings.
        hdrs = { 'User-Agent': "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11" } 
        req = urllib2.Request(self._annotation['uri'], headers = hdrs)
        soup = BeautifulSoup.BeautifulSoup(urllib2.urlopen(req))
        title = soup.title.string if soup.title else self._annotation['uri']

        #Getting the domain from the uri, and the same url magic for the domain title
        parsed_uri = urlparse(self._annotation['uri'])
        domain = '{}://{}/'.format( parsed_uri[ 0 ], parsed_uri[ 1 ] )
        domain_stripped = parsed_uri[1] 
        if parsed_uri[1].lower().startswith('www.'):
            domain_stripped = domain_stripped[4:]
        req2 = urllib2.Request(domain, headers = hdrs)
        soup2 = BeautifulSoup.BeautifulSoup(urllib2.urlopen(req2))
        domain_title = soup2.title.string if soup2.title else domain
        
        #Favicon
        favlink = soup.find("link", rel="shortcut icon")
        #Check for local/global link.
        if favlink:
            href = favlink['href']
            if href.startswith('//') or href.startswith('http'):
                icon_link = href
            else:
                icon_link = domain + href 
        else:
            icon_link = ''
        
        return {
            'title'             : title,
            'domain'            : domain,
            'domain_title'      : domain_title,
            'domain_stripped'   : domain_stripped,
            'favicon_link'      : icon_link            
        }

    def _fuzzyTime(self, date):        
        if not date: return ''
        converted = parse(date)                 
        delta = round((datetime.utcnow().replace(tzinfo=tzutc()) - converted).total_seconds())

        minute = 60
        hour = minute * 60
        day = hour * 24
        week = day * 7
        month = day * 30

        if (delta < 30): fuzzy = 'moments ago'
        elif (delta < minute): fuzzy = str(int(delta)) + ' seconds ago'
        elif (delta < 2 * minute): fuzzy = 'a minute ago'
        elif (delta < hour): fuzzy = str(int(floor(delta / minute))) + ' minutes ago'
        elif (floor(delta / hour) == 1): fuzzy = '1 hour ago'
        elif (delta < day): fuzzy = str(int(floor(delta / hour))) + ' hours ago'
        elif (delta < day * 2): fuzzy = 'yesterday'
        elif (delta < month): fuzzy = str(int(round(delta / day))) + ' days ago'
        else: fuzzy = str(converted)
        
        return fuzzy
         
    def _userName(self, user):
        if not user: return ''
        if user == '': return 'Annotation deleted.'
        else:
            return user.split(':')[1].split('@')[0]

    def _nestlist(self, part, childTable):
        outlist = []
        part = sorted(part, key=lambda reply : reply['created'], reverse=True)
        for reply in part :
            children = self._nestlist(childTable[reply['id']], childTable)
            del reply['created']
            reply['number_of_replies'] = len(children)
            outlist.append(reply)
            if len(children) > 0 : outlist.append(children)
        return outlist 
    
    def _thread_replies(self):
        childTable = {}
        reply_threaded = []
        replies = sorted(self._replies, key=lambda reply : reply['created'])

        for reply in replies :
            log.info(reply)
            pointer = reply_threaded
            for thread in reply['thread'].split('/')[1:] :
                log.info(thread)
                log.info(pointer)
                pointer = childTable[thread]

            #Add the new one.
            childTable[reply['id']] = []
            pointer.append({
                'id'            : reply['id'],
                'created'       : reply['created'],
                'text'          : reply['text'],
                'fuzzy_date'    : self._fuzzyTime(reply['updated']),
                'readable_user' : self._userName(reply['user']),
            })

        #Create nested list form
        repl = self._nestlist(reply_threaded, childTable)        
        return repl

    def _quote(self, annotation):
        if not 'target' in annotation: return ''
        quote = ''
        for target in annotation['target']:
            for selector in target['selector']:
                if selector['type'] == 'TextQuoteSelector' :
                    quote = quote + selector['exact'] + ' '
        
        return quote
    
    def generate_dict(self):
        d = {'annotation'    : self._annotation}
        d['quote'] = self._quote(self._original) if self._original else self._quote(self._annotation)
        d.update(self._url_values())
        d['fuzzy_date'] = self._fuzzyTime(self._annotation['updated'])
        d['readable_user'] = self._userName(self._annotation['user'])
        d['replies'] = self._thread_replies()

        #Count nested reply numbers
        replies = 0
        for reply in d['replies'] :
            if not isinstance(reply, types.ListType):
                replies = replies + reply['number_of_replies'] + 1
        d['number_of_replies'] = replies
        
        for key, value in d.items() :
            log.info(key + ': ' + str(value))
        return d


