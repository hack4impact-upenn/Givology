


from   base64 import urlsafe_b64encode, urlsafe_b64decode
import copy
import datetime
import sha
import hmac
import os
import pickle
import random
import re
import stat
from   string import lower, count
import time

from   django.contrib.auth import authenticate, login, logout
from   django.contrib.auth.models import User, AnonymousUser
from   django.core.cache import cache
from   django.db import connection, backend
from   django.db import models
import django.http
from   django.shortcuts import render_to_response
from   django.template.defaultfilters import slugify
from   django.template.loader import render_to_string
from   django.utils import feedgenerator
from   django.views.decorators.cache import cache_page


from   proj.giv.consts import *

from   proj.giv.htmlconv import isemailvalid, tagclean, tagunclean, forshow
from   proj.giv.utils import *
from   proj.giv.db import *
from   proj.settings import *


import proj.giv.uform as uform
from   proj.giv.models import *

from proj.giv.viewutils import *


def comingsoon(request):
    return django.http.HttpResponse('Coming Soon!')

def multimedia(request):
    blog = None
    return render_to_response(tloc+'multimedia', dictcombine(
            [maindict(request),
             {'title':'Givology: Multimedia',
              'choice0':'Community',
              'blog':blog,
              }]))
def startachapter(request):
    blog = None
    return render_to_response(tloc+'startachapter', dictcombine(
            [maindict(request),
             {'title':'Givology: Start a Chapter',
              'choice0':'Get Involved',
              'blog':blog,
              }]))

@reqUser
def invite_friends_action(request, user, profile, obj):
    blog = None
    if 'msg' not in request.POST:
        return django.http.HttpResponse('Error!')
    print request.POST
    msg = tagclean(request.POST['msg'])
    yourname = profile.name
    yourmail = user.email
    recmails = [a.strip() for a
                in request.POST['recipients'].split(',')
                if isemailvalid(a.strip())]
    if len(recmails) < 1:
        return django.http.HttpResponse(
            'looks like no valid emails?')
    if not isemailvalid(yourmail):
        return django.http.HttpResponse(
            'your email address looks invalid.')
    fr = 'giv_updates@givology.org' #yourname+'<'+yourmail+'>'
    subject = 'Invitation to Givology!'
    body = ('\n'+yourname+' ('+yourmail+
            ') has invited you to Givology! '+
            'http://www.givology.org/\n\n' + msg)
    htmlbody = render_to_string(
        tloc+'letters/spreadingword.html',
        {'email':yourmail,
         'name':yourname,
         'message':msg})
    for email in recmails:
        if islive:
            sendmail(fr, email, subject, body, htmlbody=htmlbody)
        else:
            print (fr, email, subject, body, htmlbody)
    return render_to_response(tloc+'redirect',
                              {'destination':'/account/',
                               'mesg':'Email sent! Redirecting back to your account page.'})

def setnewdonors(dict):
    print 'donorpage_donors: setting cache'

    dbpid = donorbot_profile().id
    
    return take(
        5,(p.summary() for p
           in UserProfile.objects.filter(
                kind='d').order_by('-id')
           if (not p.isanon() and
               p.has_image() and
               p.get_object().pledged_informal() > 0 and
               p.id != dbpid)
           ))

def getnewdonors():
    return setnewdonors({}) #withcache('donorpage_donors',
    #                 setnewdonors, {},
    #                 duration=1*60)


def setnewdonations(dict):
    print 'donorpage_donations: setting cache'
    
    dbdid = donorbot_donor().id
    
    return take(
        6,
        ({'donorurl' : pg.donor.profile.url(),
          'donorimg' : pg.donor.profile.get_image_url(50,50),
          'donorname': pg.donor.profile.name,
          'amount'   : pg.amount,
          'recipurl' : pg.grant.rec.profile.url(),
          'recipimg' : pg.grant.rec.profile.get_image_url(50,50),
          'recipname': pg.grant.rec.profile.name,
          'date'     : pg.created.date,
          'time'     : pg.created.time,
          }
         for pg in Paymenttogrant.objects.all(
             ).order_by('-created')
         if (not pg.isanon() and
             pg.donor.id != dbdid)
         ))

def getnewdonations():
    return setnewdonations({}) #withcache('donorpage_donations',
    #                 setnewdonations, {},
    #                 duration=1*60)

def donors(request):
    '''
    todo: what to do here?
    '''
    newdonors = getnewdonors()
    newdonations = getnewdonations()
    return render_to_response(tloc+'donors', dictcombine(
            [maindict(request),
             {'title':'Givology: Donors',
              'choice0':'Community',
              'choice1':'Donors',
              'newdonors':newdonors,
              'newdonations': newdonations,
              }]))

def donorsearch(request):
    '''
    donor search
    todo: more search criteria
    '''
    
    print request.GET
    
    getopts = []

    # note that we don't need to exclude donorbot since it has no
    # isanon attribute.
    # 
    # this would be in the wheres: 'd.id <> "%s"'%(donorbot_donor().id),
    
    froms = ['giv_donor d',
             'auth_user u',
             'giv_userprofile p',
             'giv_attrib akp',
             'giv_attrval avp',
             ]
    wheres = ['p.user_id = u.id',
              'd.profile_id = p.id',
              'p.kind="d"',
              'akp.name="isanon"',
              'akp.id=avp.attr_id',
              'avp.oid=p.id',
              'avp.tablename="giv_userprofile"',
              'avp.val="f"',
              ]
    values = []
    orderby = 'p.name asc'
    worderby = 'name_asc'
    if 'orderby' in request.GET:
        worderby = request.GET['orderby']
        orderby = {
            'joined_asc' :'u.id asc',
            'joined_desc':'u.id desc',
            'name_asc'   :'p.name asc',
            'name_desc'  :'p.name desc',
            }[worderby]
    
    
    donors = UserProfile.objects.filter(kind='d')
    name = ''
    if 'name' in request.GET:
        name = request.GET['name']
        for n in name.split():
            n = n.strip()
            if DATABASE_ENGINE == 'sqlite3':
                wheres.append('p.name glob ?')
                values.append('*'+n+'*')
            else:
                wheres.append('p.name regexp ?')
                values.append('.*'+n+'.*')
    nquery = mkquery('count(distinct p.id)', froms, wheres)
    cursor = connection.cursor()
    cursor.execute(nquery, values)
    total = int(cursor.fetchone()[0])

    blog = paginate(request, None, count0=10, width=5,
                    total = total)
    
    query = mkquery('distinct p.id', froms, wheres, orderby,
                    offset=blog['offset'],
                    count=blog['count'])
    cursor = connection.cursor()
    cursor.execute(query, values)
    
    
    blog['objects'] = [UserProfile.objects.get(id=r[0]).summary(apparent_user(request))
                       for r in cursorgen(cursor)]
    return render_to_response(tloc+'donorsearch', dictcombine(
            [maindict(request),
             {'title':'Givology: Donor Search',
              'blog': blog,
              'name': name,
              'choice0':'our-community',
              'choice1':'our-donors',
              'orderby':worderby,
              }]))

