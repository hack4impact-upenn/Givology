'''
todo: handling notifications.... :(
          will require xml parsing, a new table in the db for google checkout orders, and a new view for google to use.
          if the csrf stuff gives us sass when google tries to talk to us, then we might need to use a different domain, or do csrf ourselves...?
'''


'''
<input alt="Donate" src="https://checkout.google.com/buttons/donateNow.gif?merchant_id=542987012012612&amp;w=115&amp;h=50&amp;style=trans&amp;variant=text&amp;loc=en_US" type="image"/>

'''





from base64 import b64decode
import datetime
import pickle
import re
import traceback

import django.http

from utils import *
from models import *
from proj.settings import gcheckout_id, gcheckout_key, gcheckout_keys


def handlenotification(request):
    """
    for testing, will probably want to 
      pickle.dumps(request, open('/home/giv/analysis/'+str(datetime.datetime.now()),'wb'))
    to analyze the request.
    """
    auth = b64decode(request.META['HTTP_AUTHORIZATION'].split(' ')[1])
    authfail = True
    for i, k in gcheckout_keys:
        if auth == i+':'+k:
            authfail = False
    if authfail:
        return django.http.HttpResponseNotFound('hmm. google auth failure.  contact givology asap4.')
    xmlinput = request.POST[request.POST.keys()[0]]
    r = 'asdf'
    try: serial = re.compile('notification.*serial-number="([0-9\-]+)">').search(xmlinput).groups()[0]
    except:
        open('/home/giv/serialless.txt','w').write(xmlinput)
        return django.http.HttpResponse('')
    identifier = re.compile('<google-order-number>([a-zA-Z0-9]+)</google-order-number>').search(xmlinput).groups()[0]
    if re.compile('item-description>Plain').search(xmlinput) is not None:
        return django.http.HttpResponse(
            '<?xml version="1.0" encoding="UTF-8"?>\n' + 
            '<notification-acknowledgment \n' + 
            '          xmlns="http://checkout.google.com/schema/2" \n' + 
            '  serial-number="'+str(serial)+'" />\n')
    try:
        if GoogleOrder.objects.filter(identifier=identifier).count() == 0:
            if re.compile('new-order-notification').search(xmlinput) is not None:
                r = handlenon(xmlinput, identifier)
            else:
                return django.http.HttpResponse(
                    '<?xml version="1.0" encoding="UTF-8"?>\n' + 
                    '<notification-acknowledgment \n' + 
                    '          xmlns="http://checkout.google.com/schema/2" \n' + 
                    '  serial-number="'+str(serial)+'" />\n')
        elif re.compile('order-state-change-notification').search(xmlinput) is not None:
            r = handleoscn(xmlinput, identifier)
        elif re.compile('charge-amount-notification').search(xmlinput) is not None:
            r = handlecharge(xmlinput, identifier)
        elif re.compile('risk-information-notification').search(xmlinput) is not None:
            r = 'ok'#handlenon(xmlinput)
        else:
            #got something weird?
            open('/home/giv/proj/blah.txt','w').write(xmlinput)
            open('/home/giv/proj/err.txt','a').write('\n\n'+str(datetime.datetime.today())+'\n')
            traceback.print_exc(file=open('/home/giv/proj/err.txt','a'))
            r = 'ok'
    except:
        open('/home/giv/proj/blah.txt','w').write(xmlinput)
        open('/home/giv/proj/err.txt','a').write('\n\n'+str(datetime.datetime.today())+'\n')
        traceback.print_exc(file=open('/home/giv/proj/err.txt','a'))
        return django.http.HttpResponseNotFound('rawr! exception here!')
    if r != 'ok':
        return django.http.HttpResponseNotFound('rawr! google checkout error here! '+str(r))
    else:
        return django.http.HttpResponse(
            '<?xml version="1.0" encoding="UTF-8"?>\n' + 
            '<notification-acknowledgment \n' + 
            '          xmlns="http://checkout.google.com/schema/2" \n' + 
            '  serial-number="'+str(serial)+'" />\n')

def handlecharge(xmlinput, identifier):
    amount = re.compile('<total-charge-amount currency="USD">([0-9]+).[0-9]+</total-charge-amount>').search(xmlinput).groups()[0]
    go = GoogleOrder.objects.get(identifier=identifier)
    go.amount = amount
    go.save()
    go.charged()
    return 'ok'

def handleoscn(xmlinput, identifier):
    status = re.compile('<new-financial-order-state>([a-zA-Z_0-9]+)</new-financial-order-state>').search(xmlinput).groups()[0]
    try:
        go = GoogleOrder.objects.get(identifier=identifier)
    except:
        return 'ok'
    if go.status != status and status in ['PAYMENT_DECLINED','CANCELLED','CANCELLED_BY_GOOGLE']:
        go.chargebacked()
    go.status = status
    go.save()
    return 'ok'

def handlenon(xmlinput, identifier):
    status = re.compile('<financial-order-state>([a-zA-Z0-9]+)</financial-order-state>').search(xmlinput).groups()[0]
    try:
        uname = re.compile('Donation to wallet of username ([a-zA-Z0-9]+)').search(xmlinput).groups()[0]
    except:
        #not a donation ... it's something else...
        return 'ok'
    itemamt = re.compile('<unit-price currency="USD">([0-9]+).0*</unit-price>').search(xmlinput).groups()[0]
    totalamt = re.compile('<order-total currency="USD">([0-9]+).0*</order-total>').search(xmlinput).groups()[0]
    if (int(itemamt) > int(totalamt) or
        xmlinput.count('certificate') > 0 or
        xmlinput.count('coupon') > 0):
        return 'error: bad itememt or has certificate or coupon'
    donorid = User.objects.get(username=uname).get_profile().get_object().id
    go=None
    try:
        go = GoogleOrder.objects.get(identifier=identifier)
        go.status = status
        go.totalamt = int(itemamt)
    except:
        go = GoogleOrder(
            identifier=identifier,
            status=status,
            donorid = donorid,
            amount = int(itemamt),
            )
    go.save()
    go.charged() #this is just cuz we need instant gratification...
    return 'ok'

def getnums(s):
    digits = set(map(str,range(10)))
    nums = []
    curnum = None
    s += ' '
    for c in s:
        if c in digits:
            if curnum is None:
                curnum = 0
            curnum = (curnum*10)+(ord(c)-ord(0))
        elif curnum is not None:
            nums.append(curnum)
            curnum = None
    return nums
