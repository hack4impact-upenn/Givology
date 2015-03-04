'''
utilities of various sorts.

this file _must not_ import from models.py nor views.py, or it will break things!

'''
import os
import random
import re
import sha
import codecs
import traceback
import sys

from types import *
from string import *

import stat, time, datetime, smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


'''
constants

'''

#image viewing defaults
THUMB_WIDTH  = 100
THUMB_HEIGHT = 100
PORTRAIT_WIDTH = 250
PORTRAIT_HEIGHT = 500


'''
misc
'''

def formnum(i):
    m = i < 0
    s = ''
    i = abs(i)
    while i >= 1000:
        s = ','+('%03d'%(i%1000))+s
        i /= 1000
    s = str(i)+s
    if m: s = '-'+s
    return s



def tolist(gen):
    return [a for a in gen]

def updiv(num, den):
    a = num/den
    if num%den > 0:
        return a+1
    return a

def fif(condition, iftrue, iffalse):
    if condition:
        return iftrue
    return iffalse

def dictcombine(dlist):
    d = {}
    for dn in dlist:
        d.update(dn)
    return d

def sureint(a, default=-1):
    try:
        return int(a)
    except:
        return default

def xlogscale(finish, start=1):
    i = start
    v = 1
    while i < finish:
        yield i
        if v == 5:
            i *= 2
            v=1
        elif v == 2:
            i /= 2
            i *= 5
            v=5
        else:
            i *= 2
            v=2
def logscale(finish, start=1):
    return tolist(xlogscale(finish=finish, start=start))

def sxor(s1, s2):
    l = []
    for i in xrange(min(len(s1),len(s2))):
        l.append(chr(ord(s1[i]) ^ ord(s2[i])))
    s = ''.join(l)
    return s

def hmacsha1(key, message):
    '''
    for use with google checkout to make shopping carts
    '''
    blocksize = sha.digest_size
    opad = ['\x5c']*blocksize
    ipad = ['\x36']*blocksize
    if len(key) > blocksize:
        keyp = sha.new(key).digest()
    else:
        keyp = key+('\x00'*(blocksize-len(key)))
    return sha.new(
        sxor(opad,keyp) + 
        sha.new(
            sxor(ipad,keyp) + 
            message
            ).digest()
        ).digest()

class hell(Exception):
    def __init__(self, value="Hell!"):
        self.value = value
    def __str__(self):
        return repr(self.value)
    

def fst(x):
    a, b = x
    return a
def snd(x):
    a, b = x
    return b

#list or iterable operations
def xremoveduplicates(l):
    s = set()
    for e in l:
        if e not in s:
            s.add(e)
            yield e

def removeduplicates(l):
    return tolist(xremoveduplicates(l))

def foldl(f, i, l):
    cur = i
    for e in l:
        cur = f(cur, e)
    return cur
fold = foldl

def fromNone(f,default,n):
    if n is None:
        return default
    return f(n)
def listNone(a):
    if a is None:
        return []
    return [a]

def head(l):
    for a in l:
        return a
    return None
def lhead(l):
    return listNone(head(l))

def tail(l):
    try:
        return l[-1]
    except:
        prev = None
        for e in l:
            prev = e
        return prev
def ltail(l):
    return listNone(tail(l))
    

def cursorgen(cursor):
    while True:
        r = cursor.fetchone()
        if r is None:
            break
        yield r



def xtake(n, iterable):
    i = 0
    for a in iterable:
        if i >= n:
            break
        i+=1
        yield a
def take(n, iterable):
    return tolist(xtake(n, iterable))
def takestr(n, s):
    return ''.join(xtake(n, s))

def xmap(f, iterable):
    return (f(a) for a in iterable)

def xtakewhile(f, iterable):
    for a in iterable:
        if f(a):
            yield a
        else:
            break
def takewhile(f, iterable):
    return tolist(xtakewhile(f, iterable))

def xconcat(ll):
    '''
    combines a list of lists, so to speak
    '''
    for l in ll:
        for e in l:
            yield e
def concat(ll):
    return tolist(xconcat(ll))

def iteratef(f, seed):
    while True:
        yield seed
        seed = f(seed)

def xdrop(n, iterable):
    i = 0
    for a in iterable:
        if i >= n:
            yield a
        i+=1
def drop(n, iterable):
    if type(iterable) == 'string':
        if n >= len(iterable):
            return ''
        else:
            return iterable[n:]
    return tolist(xdrop(n, iterable))
def ixdrop(n, indexable, ifun=None):
    if ifun is None:
        for i in xrange(n, len(indexable)):
            yield indexable[i]
    else:
        for i in xrange(n, len(indexable)):
            yield ifun(i,indexable)
def idrop(n, indexable, ifun=None):
    return tolist(ixdrop(n, indexable, ifun))

def fromNone(default, a):
    if a is None:
        return default
    return a


# quarters: (year, quarternum) eg, (2008,1) means jan 1 2008 through mar 31, 2008

# getquarter :: datetime -> quarter
def getquarter(d):
    q = 1
    if d.month in [4,5,6]:    q = 2
    if d.month in [7,8,9]:    q = 3
    if d.month in [10,11,12]: q = 4
    return (d.year, q)

# quarterstart :: quarter -> datetime
def quarterstart(q):
    return datetime.datetime(
        year=fst(q),
        month=((snd(q)-1)*3)+1,
        day=1)

def quarternext(qt):
    y, q = qt
    if q == 4:
        return (y+1,1)
    return (y,q+1)

# quarterend :: quarter -> datetime
def quarterend(q):
    return (
        quarterstart(quarternext(q)) +
        datetime.timedelta(microseconds=-1))

# quarterfilter :: quarter ->
#                  quarter ->
#                  djangoresultset ->
#                  djangoresultset
def quarterfilter(q0, q1, rs, field='created'):
    return rs.filter(
        kwargs={field+'__gte':quarterstart(q0)}
        ).filter(
        kwargs={field+'__lt':quarterstart(quarternext(q1))}
        )






'''
encoding
'''

def toutf(s):
    if isinstance(s,unicode):
        return s
    assert isinstance(s,str)
    r = None
    for e in ['ascii','utf-8','iso-8859-1',
              'Big5','GB2312','HZ','GBK',
              'Shift-JIS','CP932',
              ]:
        try:
            r = codecs.decode(s,e)
            break
        except: pass
    return r

def ddquote(c):
    if c == '"': return '""'
    else:        return c
def csvencode(s):
    return '"'+''.join([ddquote(c) for c in s])+'"'







'''
tag stuff
'''
TAG_MAX_LENGTH = 30

STAFF_TAGS = set([
        'notes from the field',
        'givology news',
        'givology frontpage',
        ])


def tags2str(tags):
    return ', '.join(tags)



def name2username(name, i):
    name1 = name.strip().lower()
    name2 = ''
    for c in name1:
        if (not c.isalnum() and c != ' '):
            break
        name2 += c
    names = [n.strip() for n in name2.split(' ') if len(n)>0]
    username = ''
    if len(names) < 1:
        username = 'asdf'+str(i)
    else:
        username = ''.join(
            [n[0] for n in names]+
            [names[-1][1:]])
    if i == 0:
        return username
    return username+str(i)
    
import string
username_allowed_characters = set(string.ascii_lowercase + string.ascii_uppercase + string.digits + '.@+-_')
def is_valid_username(username):
    return set(username) <= username_allowed_characters


def paginate(request, queryset=None, count0=10, page0=0, width=5,
             total=None):
    d = {}
    page = page0
    count = count0
    try:
        page = int(request.GET['page'])
        if page < 0: page = 0
    except: page = 0
    try:
        count = int(request.GET['count'])
        if count < 1: count = 1
    except: count = count0
    
    d['count0'] = count0
    d['count']  = count
    d['page0']  = page0
    d['page']   = page
    
        
    oc = total
    if total is None:
        if queryset is None:
            oc = 0
        else:
            try:
                oc = queryset.count()
            except:
                oc = len(queryset)
    offset = 0
    lastpage = oc/count
    if oc % count == 0:
        lastpage -= 1
    if oc > 0:
        page = min(page, lastpage)
        offset = page * count
        rem = oc - offset
        if queryset is None:
            objects = []
        else:
            objects = queryset[offset:offset+min(rem,count)]
    else:
        objects = []
    
    d['objects'] = objects
    d['paginated'] = lastpage>0
    d['totalpages'] = lastpage+1
    d['pages'] = range(max(0,page-width),
                       min(page+width,lastpage)+1)
    d['prev'] = max(page-1,0)
    d['next'] = max(min(page+1,lastpage), 0)
    d['offset'] = offset
    
    return d


def addhttproot(s, root='https://www.givology.org'):
    return re.sub('"(/[^"]+)"',
                  '"%s\\1"'%(root),
                  s)


def randint56():
    i = 0
    s = os.urandom(7)
    for c in s:
        i <<= 7
        i |= ord(c)
    return i







'''
email stuff
'''


def sendmail(fr, to, subject, body, server=None, htmlbody=None):
    '''
    sending an email, basically
    
    todo: use email class (import email) to handle non-english characters and punctuation...
    '''
    if server is None:
        server = smtplib.SMTP('smtp.webfaction.com')
        server.login('giv_updates','whatwouldschneierdo')
    subject.replace('\n','')
    msg = None
    if htmlbody is None:
        msg = MIMEText(body)
    else:
        msg = MIMEMultipart('alternative')
        part1 = MIMEText(body, 'plain')
        part2 = MIMEText(htmlbody, 'html')
        msg.attach(part1)
        msg.attach(part2)
    msg['Subject'] = subject
    msg['From'] = fr
    msg['To'] = to
    server.sendmail(fr, to, msg.as_string())
    return server



def hashpassword(pw,salt=None):
    """
    password hashing as done in django's default sha1 method.
    """
    if salt is None:
        salt = sha.new(str(random.random())).hexdigest()[:5]
    hsh = sha.new(salt+str(pw)).hexdigest()
    return '%s$%s$%s' % ('sha1', salt, hsh)


def gettraceback():
    e, f, t = sys.exc_info()
    return traceback.format_exc(t)
