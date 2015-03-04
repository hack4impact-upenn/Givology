#!/usr/bin/python
'''
for things to run periodically from cron or whatever
'''

#trying to set up the path to access our stuff.... will need some work
import sys
sys.path = ['/django/giv/proj','/home/giv/webapps/django/proj']+sys.path
#another option is to just 
#   echo "from proj.giv.cron import *; main()" | python manage.py shell"
#or something



import os, stat, time, datetime
from string import *

from proj.settings import *
from proj.giv.utils import *
from proj.giv.models import *



def updatepayments():
    '''
    updates all payments. make this a daily job?
    '''
    
    conftime = (datetime.datetime.today() - 
                datetime.timedelta(days=32))
    ncpw = [pw for pw in Paymenttowallet.objects.filter(
        confirmed=False).filter(
        modified__lt=conftime)]
    for pw in ncpw:
        pw.confirmed=True
        pw.save()
    ncpg = []
    for donor in [pw.donor for pw in ncpw]:
        for pg in Donor.paymenttogrant_set.filter(
            confirmed=False).order_by('created'):
            if pg.amount > donor.have_confirmed():
                break
            pg.confirmed = True
            pg.save()
            ncpg.append(pg)
    mncg = set([pg.grant for pg in ncpg])
    ncg = set([g for g in mncg if g.have_confirmed() >= g.want])
    # ncg is the list of grants that are now completed and should be payed.
    for g in ncg:
        g.confirmed = True
        g.save()
        #todo: email people? pay people?
    return



if __name__ == '__main__':
    pass #todo: put things to do here
