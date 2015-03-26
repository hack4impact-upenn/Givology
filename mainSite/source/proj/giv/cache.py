
import random
import time

from   django.core.cache import cache



cacheduration=100000

def fromcache(cachename, default='assplode'):
    try: r = cache.get(cachename, default)
    except: r = default
    if r == 'assplode':
        raise hell
    return r

def invalidatecache(cachename, duration=cacheduration):
    try: cache.set(cachename,'_*_invalid_*_',cacheduration)
    except: pass
    return

def withcache(cachename, f, d, duration=cacheduration):
    #return f(d)
    try:
        retval = cache.get(cachename, None)
        while retval is None or retval == '_*_invalid_*_':
            cache.delete(cachename)
            tmp = f(d)
            retval = cache.get(cachename, None)
            if retval == '_*_invalid_*_':
                continue
            else:
                cache.set(cachename, tmp, duration)
                #print 'cached '+cachename
                retval = tmp
    except:
        #something awkward happened...
        return f(d)
    return retval
                
    
