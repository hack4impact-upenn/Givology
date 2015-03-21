

import re
import copy

from   django.core.cache import cache

res = {}
def mcomp(s, flags=None):
    global res
    if s not in res:
        res[s] = re.compile(s,re.DOTALL)
    return res[s]

def tagclean(s0):
    s = copy.copy(s0)
    s = mcomp(r'(>)').sub(r'&gt;',s)
    s = mcomp(r'(<)').sub(r'&lt;',s)
    s = mcomp(r'(")').sub(r'&quot;',s)
    s = mcomp(r"(')").sub(r'&#39;',s)
    s = mcomp(r'(\\not)').sub(r'&not;',s)
    s = mcomp(r'(\\mul)').sub(r'&middot;',s)
    s = mcomp(r'(\\div)').sub(r'&divide;',s)
    s = mcomp(r'(\\deg)').sub(r'&deg;',s)
    s = mcomp(r'(\\mu)').sub(r'&micro;',s)
    return s

def tagunclean(s0):
    s = copy.copy(s0)
    s = mcomp(r'(&gt;)').sub(r'>',s)
    s = mcomp(r'(&lt;)').sub(r'<',s)
    s = mcomp(r'(&quot;)').sub(r'"',s)
    s = mcomp(r"(&#39;)").sub(r"'",s)
    s = mcomp(r'(&not;)').sub(r'\\not',s)
    s = mcomp(r'(&middot;)').sub(r'\\mul',s)
    s = mcomp(r'(&divide;)').sub(r'\\div',s)
    s = mcomp(r'(&deg;)').sub(r'\\deg',s)
    s = mcomp(r'(&micro;)').sub(r'\\mu',s)
    return s

def remove_bbtags(s):
    s = mcomp('\[[^\]]*\]').sub('',s)
    return s

def cleanseonetag(s,tagname,parent=True,singleton=True,fauxsingleton=True):
    re1 = mcomp('&lt;\s*'+tagname+'(?P<attributes>.*?)&gt;(?P<children>.*?)&lt;/'+tagname+'&gt;')
    re2 = mcomp('&lt;\s*'+tagname+'(?P<attributes>.*?)/&gt;')
    re3 = mcomp('&lt;\s*'+tagname+'(?P<attributes>.*?)&gt;')
    if parent:
        ms = re1.search(s)
        if ms:
            return (s[0:ms.start()] + 
                    '<' +tagname+remove_bbtags(tagunclean(ms.group('attributes')))+'>' +
                    remove_bbtags(ms.group('children')) +
                    '</'+tagname+'>' +
                    s[ms.end():])
    if singleton:
        ms = re2.search(s)
        if ms:
            return (s[0:ms.start()] + 
                    '<' +tagname+remove_bbtags(tagunclean(ms.group('attributes')))+'/>' +
                    s[ms.end():])
    if fauxsingleton:
        ms = re3.search(s)
        if ms:
            return (s[0:ms.start()] + 
                    '<' +tagname+remove_bbtags(tagunclean(ms.group('attributes')))+'>' +
                    s[ms.end():])
    return 0

def cleanseonetagrepeat(s,tagname,parent=True,singleton=True,fauxsingleton=True):
    while True:
        s1 = cleanseonetag(s,tagname,parent,singleton,fauxsingleton)
        if s1 == 0:
            break
        else:
            s = s1
    return s


def applymaxlen(s, maxlen):
    if maxlen is None:
        return s
    if len(s) > maxlen:
        s = s[:maxlen-3]+'...'
    return s

def stripshow(s, maxlen=None):
    '''
    like forshow() but strips out anything html-ish.
    '''
    cachename = 'stripshow_%i'%(hash(s))
    try: spn = cache.get(cachename, None)
    except: spn = None
    if spn is not None:
        s0, s1 = spn
        if s0 == s:
            return applymaxlen(s1,maxlen)
    s0 = copy.deepcopy(s)
    
    s = mcomp('&lt;(.*?)&gt;').sub(' ',s)
    s = ' '.join(s.split())
    
    try: cache.set(cachename,(s0,s),60)
    except: pass
    return applymaxlen(s,maxlen)
    
    

def forshow(s, shouldparagraphify=True):
    cachename = 'forshow_%i'%(hash(s))
    try: spn = cache.get(cachename,None)
    except: spn = None
    if spn is not None:
        s0, s1 = spn
        if s0 == s:
            return s1
    s0 = copy.deepcopy(s)
    
    s = s.strip()
    
    imgre = mcomp('&lt;\s*?[iI][mM][gG][ \\t\\n\\r]+(.*?)[sS][rR][cC]=&quot;([a-zA-Z0-9=_:;\\,\\-\\.\\?/~` ]+?)&quot;(.*?)/?&gt;')
    are = mcomp('&lt;[ \\t\\n\\r]*?[aA][ \\t\\n\\r]+(.*?)[hH][rR][eE][fF]=&quot;([a-zA-Z0-9=&@_:;\\,\\.\\-\\?/~`\\\\ ]+?)&quot;.*?&gt;(.*?)&lt;/[aA]&gt;')
    
    for tag in ['object','iframe']:
        s = cleanseonetagrepeat(s,tag)
    for tag in ['param','embed']:
        s = cleanseonetagrepeat(s,tag,fauxsingleton=True)
    
    while True:
        s = ' '+s+' '
        ms = imgre.search(s)
        if ms:
            ms.start()
            t = ms.groups()[1]
            try:
                t2 = ms.groups()[2]
                t2 = mcomp('alt=&quot;(.*?)&quot;').sub('alt="\\1"',t2)
                t2 = mcomp('height=&quot;(.*?)&quot;').sub('height="\\1"',t2)
                t2 = mcomp('width=&quot;(.*?)&quot;').sub('width="\\1"',t2)
            except:
                t2 = ''
            if 'javascript:' in t.lower():
                t = ''
            s = (s[0:ms.start()] + 
                 '<img src="%s"%s />'%(t,t2) + 
                 s[ms.end():])
        else:
            break
    while True:
        s = ' '+s+' '
        ms = are.search(s)
        if ms:
            ms.start()
            t = ms.groups()[1]
            if 'javascript:' in t.lower():
                t = ''
            s = (s[0:ms.start()] + 
                 '<a href="%s">%s</a>'%(t, ms.groups()[2]) + 
                 s[ms.end():])
        else:
            break
    
    #italics, bold, underline...
    s = mcomp('&lt;small&gt;(.*?)&lt;/small&gt;').sub('<small>\\1</small>',s)
    s = mcomp('&lt;[iI]&gt;(.*?)&lt;/[iI]&gt;').sub('<em>\\1</em>',s)
    s = mcomp('&lt;em&gt;(.*?)&lt;/em&gt;').sub('<em>\\1</em>',s)
    s = mcomp('&lt;[bB]&gt;(.*?)&lt;/[bB]&gt;').sub('<strong>\\1</strong>',s)
    s = mcomp('&lt;strong&gt;(.*?)&lt;/strong&gt;').sub('<strong>\\1</strong>',s)
    s = mcomp('&lt;[uU]&gt;(.*?)&lt;/[uU]&gt;').sub('<u>\\1</u>',s)
    s = mcomp('&lt;span style=&quot;text-decoration: underline;&quot;&gt;(.*?)&lt;/span&gt;').sub('<u>\\1</u>',s)
    s = mcomp('&lt;[dD][eE][lL]&gt;(.*?)&lt;/[dD][eE][lL]&gt;').sub('<del>\\1</del>',s)
    s = mcomp('&lt;span style=&quot;text-decoration: line-through;&quot;&gt;(.*?)&lt;/span&gt;').sub('<del>\\1</del>',s)
    #lists
    s = mcomp('&lt;[uU][lL]&gt;([ \\r\\n\\t]*)(.*?)([ \\r\\n\\t]*)&lt;/[uU][lL]&gt;').sub('<ul>\\2</ul>',s)
    s = mcomp('&lt;[oO][lL]&gt;([ \\r\\n\\t]*)(.*?)([ \\r\\n\\t]*)&lt;/[oO][lL]&gt;').sub('<ol>\\2</ol>',s)
    s = mcomp('([ \\r\\n\\t]*)&lt;[lL][iI]&gt;([ \\r\\n\\t]*)(.*?)([ \\r\\n\\t]*)&lt;/[lL][iI]&gt;([ \\r\\n\\t]*)').sub('<li>\\3</li>',s)
    s = mcomp('&lt;br ?/?&gt;').sub(' \n ',s)
    #s = mcomp('&lt;br&gt;').sub(' \n ',s)
    
    #monospace
    s = mcomp('&lt;[mM]&gt;(.*?)&lt;/[mM]&gt;').sub('<span style="font-family: monospace; white-space: pre;">\\1</span>',s)
    
    s = mcomp('&lt;/?[pP]&gt;').sub('',s)

    
    
    if shouldparagraphify:
        s = paragraphify(s)
    try: cache.set(cachename,(s0,s),60)
    except: pass
    return s


def paragraphify(s0):
    '''
    takes string s0 and tries to detect paragraphs in it
    '''
    linelist = s0.split('\n')+['']
    prevline = None
    prevprevline = None
    nlinelist = []
    for line in linelist:
        if prevline is not None:
            if prevline != '' and (prevprevline == '' or prevprevline is None) and line == '':
                nlinelist.append('<p>'+prevline+'</p>')
            elif prevline == '' and prevprevline != '' and line != '':
                pass
            else:
                nlinelist.append(''+prevline+'<br />')
        prevprevline = copy.deepcopy(prevline)
        prevline = copy.deepcopy(line)
    linelist = nlinelist
    s = ''.join(linelist)
    return s

def isemailvalid(emailaddress):
    if len(emailaddress) > 5:
        if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,5}|[0-9]{1,3})(\\]?)$", emailaddress) != None:
            return True
    return False
