#!/usr/bin/env python
# encoding: utf-8
"""
iccdb-fetch.py

Created by FI$H 2000 on 2011-06-09.
Copyright (c) 2011 OST, LLC. All rights reserved.
"""

import sys, os, re, urllib2, urlparse, random, simplestats
from BeautifulSoup import BeautifulSoup, Tag

try:
    import ujson as json
except ImportError:
    print "--- Loading yajl in leu of ujson"
    try:
        import yajl as json
    except ImportError:
        print "--- Loading simplejson in leu of yajl"
        try:
            import simplejson as json
        except ImportError:
            print "--- Loading stdlib json module in leu of simplejson"
            import json

drycreek = "http://www.drycreekphoto.com/icc/"
diskloc = '/Users/fish/Dropbox/imagekit/django-imagekit-f2k/iccdb'
htmldataloc = os.path.join(diskloc, "htmldata")
jsoncacheloc = os.path.join(diskloc, "jsoncache")
jsonfilename = "iccdb.json"

htmlbits = ['a', 'span', 'div', 'p', 'li', 'ul']
htmlbites = { 'href': set(), 'class': set(), 'id': set(), 'name': set(), }

urltxt = lambda u: urllib2.urlopen(u).read()
soup = lambda uu: BeautifulSoup(urltxt(uu))
stew = lambda uu: BeautifulSoup(uu)

avg = simplestats.mean
stddev = simplestats.stddev

def writeout(htmlmorsel, morselname):
    with open(os.path.join(htmldataloc, morselname), "w+b") as f:
        f.write(htmlmorsel)
        f.flush()
        f.close()

def jsonpuke(thingy, pukename):
    with open(os.path.join(jsoncacheloc, pukename), "w+b") as f:
        json.dump(thingy, f, indent=4)

def jsonhangover(pukename):
    out = None
    if os.path.exists(os.path.join(jsoncacheloc, pukename)):
        with open(os.path.join(jsoncacheloc, pukename), "r+b") as f:
            out = json.load(f)
    return out

class Nil():
    def write(self, s):
        pass


def main():
    
    # nix stdout
    
    ICCDB = {}
    cachedata = jsonhangover(jsonfilename)
    
    if not cachedata:
        # download everything
        
        sp = soup(drycreek)
        navs = sp.findAll('a', attrs={ 'class': "nav", })
        
        placehrefs = map(lambda n: n.attrMap['href'].split('#')[0], navs)
        iccplacehrefs = map(lambda pu: urlparse.urljoin(drycreek, pu), placehrefs)
        #iccplacerawhtml = map(lambda ur: urltxt(ur), iccplacehrefs)
        
        print ""
        print "### Fetching ICC database corpus from %s..." % drycreek
        print ""
        
        i = 0
        for href in iccplacehrefs:
            rawhtml = urltxt(href)
            nameout = os.path.basename(href)
            ICCDB.update({ nameout.split('_')[0]: { 'url': href, 'filename': nameout, 'htmldata': rawhtml, 'idx': i, }, })
            #writeout(rawhtml, nameout)
            print "--- %30s \t ~ %s bytes" % (nameout, len(rawhtml))
            i += 1
        
        print ""
        
        if not len(ICCDB):
            print "xxx Found no data in JSON cache and nothing at the link: %s" % drycreek
            sys.exit(1)
        
        print ">>> Writing the database to a JSON cache..."
        jsonpuke(ICCDB, jsonfilename)
        
    else:
        print "### Reloading ICC database corpus from JSON cache..."
        print "### Found %s place items total" % len(cachedata)
        
        print ""
        print ""
        
        #print cachedata.keys()
        #print [(k, ', '.join(v.keys())) for k, v in cachedata.items()]
        
        print ""
        print ""
        
        #for trip in sorted([(cachedata[key].get('idx'), key, cachedata[key]) for key in cachedata.keys()], key=lambda tup: tup[0], reverse=False):
        #    ICCDB.update({ trip[1]: dict(trip[2]), })
        
        ICCDB.update(cachedata)
        
        print [(k, ', '.join(v.keys())) for k, v in ICCDB.items()]
        
        print ""
        print ""
        
        
        
        
        
        
    htmlsizeseq = [len(ICCDB[hd].get('htmldata')) for hd in ICCDB.keys()]
    print "### Total %s raw HTML files, ~ %10d bytes " % (len(ICCDB), sum(htmlsizeseq))
    print "### Min %10d \t\t Max    %10d" % (min(htmlsizeseq), max(htmlsizeseq))
    print "### Avg %10d \t\t StdDev %10d" % (avg(htmlsizeseq), stddev(htmlsizeseq))
    
    for place, placedata in ICCDB.items():
        soup = 
        
        
        soup = None
        
    
    
    print ""
    print ""
    
    # FUCK ALL THAT
    sys.exit(0)
    


if __name__ == '__main__':
    main()



#random.choice(iccplacerawhtml)[250:500]
#onehtml = random.choice(iccplacerawhtml)



