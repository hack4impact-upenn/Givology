


from   proj.giv.utils import *
from   proj.settings import *
from   django.db import connection, backend


def perdb(s):
    # %s seems to work across the board
    return s.replace('?','%s')
    #if DATABASE_ENGINE == 'sqlite3':
    #    return s
    #if DATABASE_ENGINE == 'mysql':
    #    return s.replace('?','%s')

def mkquery(select, froms, wheres=None, orderby=None,
            offset=None, count=None):
    l = ['select ',
         select,
         ' from ',
         ', '.join(froms)]
    if wheres is not None:
        l.append(' where (')
        l.append(') and ('.join(wheres))
        l.append(')')
    if orderby is not None:
        l.append(' order by ')
        l.append(orderby)
    if   (offset is not None and
          count is not None):
        l.append(' limit %i,%i'%(offset, offset+count))
    elif (offset is None and
          count is not None):
        l.append(' limit %i'%(count))
    return perdb(' '.join(l))
                   
def runquery(query,values=[],n=1,r=1):
    cursor = connection.cursor()
    cursor.execute(query, values)
    def ono(o):
        if n == 1:
            return o[0]
        if n is None:
            return o
        return o[0:n]
    if r == 1:
        return ono(cursor.fetchone())
    elif r is None:
        return (ono(o) for o in cursor.fetchall())
    return [ono(o) for o in cursor.fetchmany(r)]

