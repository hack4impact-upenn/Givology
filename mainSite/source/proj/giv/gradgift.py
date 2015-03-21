
from django.shortcuts import render_to_response
from proj.giv.messaging import *
from proj.giv.viewutils import *
from proj.giv.models import *
from datetime import date


def gradgift(request):
    if request.method=='POST':
        return gradgiftpost(request)
    u = apparent_user(request)
    p = None
    d = None
    try:
        p = u.get_profile()
        assert p.kind=='d'
        d = p.get_object()
    except:
        u = None
        p = None
        d = None
    email = ''
    sendername = ''
    if u is not None and u.email is not None:
        email = u.email
    if p is not None and p.name is not None:
        sendername = p.name
    todayord = date.today().toordinal()
    dds = [{'ordinal':i,
            'date':date.fromordinal(i).strftime(
                "%A %B %d, %Y")}
           for i in xrange(todayord,todayord+365)]
    return render_to_response(tloc+'gradgift.html',dictcombine(
        [maindict(request),
         {'title':'Givology: Gift of Graduation',
          'choice0':'Community',
          'email':email,
          'sendername':sendername,
          'deliverydates':dds,
          }]))

def e2n(s):
    if s is None or s.strip() == '':
        return None
    return s

def gradgiftpost(request):
    u = apparent_user(request)
    p = None
    d = None
    try:
        p = u.get_profile()
        assert p.kind=='d'
        d = p.get_object()
    except:
        u = None
        p = None
        d = None
    g = GradGift(
        creator = d,
        address = request.POST['address'],
        schoolname = e2n(request.POST.get('schoolname')),
        hometown = e2n(request.POST.get('hometown')),
        shoutout = e2n(request.POST.get('shoutout')),
        senderemail = request.POST['senderemail'],
        recipientemail = e2n(request.POST.get('recipientemail')),
        sendername = e2n(request.POST.get('sendername')),
        recipientname = e2n(request.POST.get('recipientname')),
        message = request.POST.get('message'),
        )
    try:
        g.deliverydate = date.fromordinal(
            int(request.POST['deliverydate']))
    except: pass
    g.save()
    
    return render_to_response(tloc+'gradgiftconfirm.html',dictcombine(
        [maindict(request),
         {'title':'Givology: Gift of Graduation -- Confirm',
          'choice0':'Community',
          'gift':g,
          }]))
    

