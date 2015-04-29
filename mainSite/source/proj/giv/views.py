# Create your views here.


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
import sys
import time

from   django.contrib.auth import authenticate, login, logout
from   django.contrib.auth.models import User, AnonymousUser
from   django.db import connection, backend
from   django.db import models
import django.http
from   django.shortcuts import render_to_response
from   django.template.defaultfilters import slugify
from   django.template.loader import render_to_string
from   django.utils import feedgenerator
from   django.views.decorators.cache import cache_page
from   django.utils.translation import ugettext as _

from   proj.giv.consts import *

import proj.giv.captcha as captcha
from   proj.giv.htmlconv import tagclean, tagunclean, forshow, isemailvalid
from   proj.giv.utils import *
from   proj.giv.db import *
from   proj.settings import *


import proj.giv.uform as uform
from   proj.giv.models import *


from proj.giv.viewutils import *

from proj.giv.cache import *
from proj.giv.community import *
from proj.giv.groups import *
from proj.giv.messaging import *
from proj.giv.profile import *
from proj.giv.gradgift import *

from django.utils import simplejson
from django.views.decorators.csrf import csrf_protect, csrf_exempt
import json

@adminOnly
def memcachedpage(request,user):
    try:
        import memcache
    except ImportError:
        raise django.http.Http404

    host = memcache._Host(CACHE_BACKEND[12:])
    host.connect()
    host.send_cmd("stats")
    lines = []
    while True:
        try: lines.append(host.readline())
        except: break
    host.close_socket()
    return django.http.HttpResponse('\n<br>'.join(lines))


def getsomedone(kind=None):
    """
    generator for recipients that will produce recipients of different countries.

    the loop first gets closest-to-done recipient, then adds a caveat to the 'wheres' list, so that the next one to be found is going to be not from that country. when one can not be found, it breaks from the loop.
    """
    wheres = ['r.id=g.rec_id',
              'p.id=r.profile_id',
              'avc.oid=p.id',
              'avc.tablename="giv_userprofile"',
              'akc.name="country"',
              'akc.id=avc.attr_id',
              'g.percent_very_informal<100',
              ]
    vals = []
    if kind is not None:
        wheres += ['p.kind="'+kind+'"']
    while True:
        try:
            pid = runquery(
                mkquery('p.id',
                        ['giv_userprofile p',
                         'giv_recipient r',
                         'giv_grant g',
                         'giv_attrib akc',
                         'giv_attrval avc'],
                        wheres,
                        orderby='-g.percent_very_informal',
                        count=1),
                vals,1,1)
        except:
            print wheres
            print vals
            print 'broken!'
            break
        yield pid
        p = UserProfile.objects.get(id=pid)
        wheres += ['avc.val <> %s']
        vals += [get_attr('country',p,'asdf')]

def getnearlydone_f(d):
    """
    lists students/projects, showing nearest to be done, varying by country, first, then nearest to be done (ignoring country), then anything that is left.
    """
    gs = Grant.objects.all()
    if d['kind'] is not None:
        gs = gs.filter(rec__profile__kind=d['kind'])
    gs1 = gs.filter(percent_very_informal=100)
    gs = gs.filter(percent_very_informal__lt=100)
    gs = gs.order_by('-percent_very_informal')
    ignores = d.get('ignores',set([]))
    return take(
        d['count'],
        (p.summary() for p in
         (UserProfile.objects.get(id=pid)
          for pid in xremoveduplicates(
              xconcat([getsomedone(kind=d['kind']),
                       (g.rec.profile.id for g in gs),
                       (g.rec.profile.id for g in gs1)]))
          if pid not in ignores)
         if p.get_object().approved)
        )


def getnearlydone(count=5, kind=None):
    return withcache('nearlydone'+'_'+str(count)+'_'+str(kind),
                     getnearlydone_f,
                     {'kind':kind, 'count':count}, duration=60)

def getFeatured_f(d):
    fps = FeaturedProfile.objects.all().order_by('-featuretime')
    if d['kind'] is not None:
        fps = fps.filter(profile__kind=d['kind'])
    count = 1000000
    if d['count'] is not None:
        count = d['count']
    return [fp.profile.summary() for fp in
            xtake(count,fps)]

def getFeatured(count=5, kind=None):
    return withcache('featuredprofiles'+'_'+str(count)+'_'+str(kind),
                     getFeatured_f,
                     {'kind':kind, 'count':count}, duration=60)

def getFeaturedThenNearlyDone_f(d):
    df = dict(d)
    lf = getFeatured_f(df)
    if d['count'] is not None and len(lf) >= d['count']:
        return lf
    dn = dict(d)
    if d['count'] is not None:
        dn['count'] -= len(lf)
    dn['ignores'] = set([p['id'] for p in lf])
    ln = getnearlydone_f(dn)
    return lf+ln

def getFeaturedThenNearlyDone(count=5, kind=None):
    return withcache('featuredprofilesnearlydone'+'_'+str(count)+'_'+str(kind),
                     getFeaturedThenNearlyDone_f,
                     {'kind':kind, 'count':count}, duration=60)

def getimpactthisweek_f(d):
    genesis= datetime.datetime(year=2008, month=8, day=15)
    weekago=(datetime.datetime.now() - datetime.timedelta(days=7))

    dbd = donorbot_donor()

    dollars = 0
    try: dollars += int(Constants.objects.get(name='microfundraisers').value)
    except: pass
    ndollars = 0
    payments = 0
    npayments = 0
    studs = set()
    nstuds = set()
    projs = set()
    nprojs = set()


    # impacted_students_of = {}
    # for pg in Paymenttogrant.objects.exclude(donor__id = dbd.id):
    #     rp = pg.grant.rec.profile
    #     rid = rp.id
    #     rt = rp.kind
    #     #if not pg.grant.rec.curgrant().iscomplete():
    #     #    continue
    #     if rt == 'p':
    #         attrs = get_attrs(rp)
    #         if attrs['numhelped'] is not None:
    #             try:
    #                 impacted_students_of[rid] = int(attrs['numhelped'])
    #             except ValueError:
    #                 pass
    #     elif rt == 's':
    #         impacted_students_of[rid] = 1

    for pg in Paymenttogrant.objects.exclude(donor__id = dbd.id):
        # if pg.donor.id == dbd.id: continue
        rp = pg.grant.rec.profile
        rid = rp.id
        rt = rp.kind
        if pg.created > weekago:
            ndollars += pg.amount
            npayments += 1
            {'s':nstuds,'p':nprojs}[rt].add(rid)
        dollars += pg.amount
        payments += 1
        {'s':studs,'p':projs}[rt].add(rid)

    legacy_hours = 80000

    return {
        'title'   : 'Impact this week',
        'dollars'  : formnum(dollars),
        'ndollars' : formnum(ndollars),
        'payments'  : formnum(payments),
        'npayments' : formnum(npayments),
        'studs'  : len(studs),
        #'studs'  : sum(impacted_students_of.values()),
        'nstuds' : len(nstuds),
        'projs'  : len(projs),
        'nprojs' : len(nprojs),
        'ndonors' : Donor.objects.filter(
            profile__user__date_joined__gt=weekago).count(),
        'donors' : Donor.objects.all().count(),
        'volmins' : sum([vw.minutes for vw in
                         VolunteerWork.objects.all()]),
        'volhours' : formnum(   legacy_hours
                              + int(sum([vw.minutes for vw in
                                         VolunteerWork.objects.all()]) / 60.0)),
        'nvolmins' : sum([vw.minutes for vw in
                          VolunteerWork.objects.filter(
                              when__gt=weekago)])
        }

def givrss(request, tags):
    tags = [a.strip() for a in tags.split(',')]
    for tag in tags:
        if tag not in ['givology news',
                       'notes from the field',
                       'givology frontpage']:
            return django.http.HttpResponseNotFound('404: no such rss feed; did you perhaps leave out a space?')
    bpss = [take(10, BlogPost.objects.filter(
        tags__tag=tag).order_by(
        '-created')) for tag in tags]
    bpids = set([])
    bplist = []

    while len(bpss) > 0:
        for bps in bpss:
            if len(bps) < 1:
                bpss.remove(bps)
        newestbps = None
        for bps in bpss:
            if ( newestbps is None or
                 newestbps[0].created < bps[0].created):
                newestbps = bps
        if newestbps is not None:
            if newestbps[0].id not in bpids:
                bplist.append(newestbps[0])
                bpids.add(newestbps[0].id)
            bpss.remove(newestbps)
            bpss.append(drop(1,newestbps))
    print [bp.id for bp in bplist]


    f = feedgenerator.RssUserland091Feed(
        title=u'Givology RSS',
        description=u'Givology RSS Feed',
        link=u'http://www.givology.org/',
        feed_url=u'http://www.givology.org/',
        )
    for bp in bplist:
        f.add_item(
            title=toutf(bp.subject),
            description=toutf(bp.subject),
            author_name=toutf(bp.author.get_profile().name),
            link=u'http://www.givology.com/~%s/blog/%d/'%(bp.author.username,bp.id),
            feed_url=u'http://www.givology.com/~%s/blog/%d/'%(bp.author.username,bp.id),
            pubdate = bp.created,
            )
    return django.http.HttpResponse(f.writeString('utf8'))




def socialactionsfeed(request):
    f = feedgenerator.RssUserland091Feed(
        title=u'Givology Students and Projects',
        description=u'Recently added Givology Students and Projects',
        link=u'https://www.givology.org/',
        feed_url=u'https://www.givology.org/',
        )
    def kindof(u):
        try: return u.get_profile().kind in ['s','p']
        except: return False
    for u in take(50,(
        u for u in User.objects.all().order_by('-date_joined')
        if kindof(u)
        )):
        p = u.get_profile()
        ps= p.summary()
        f.add_item(
            title=toutf(ps['name']),
            link=toutf('https://www.givology.org'+ps['url']),
            feed_url=toutf('https://www.givology.org'+ps['url']),
            description=toutf(ps['summary']),
            pubdate = u.date_joined,
            )
    return django.http.HttpResponse(f.writeString('utf8'))



def getimpactthisweek():
    return withcache('impactthisweek',
                     getimpactthisweek_f,
                     {}, duration=60*60)

def index(request):
    '''
    main page
    '''
    user = apparent_user(request)

    #for statistical info
    logvisit('index',request)

    headlines = [p.dicttorender() for p in
                 take(3,BlogPost.objects.filter(
                     tags__tag='givology frontpage').order_by(
                          '-created'))]

    return render_to_response(tloc+'main', dictcombine(
            [maindict(request),
             {'title':'Givology',
              'choice0': 'Give',
              'impact':getimpactthisweek(),
              'numdonors' : formnum(Donor.objects.all().count()),
              'headlines':headlines,
              'featured_recipients': (getFeaturedThenNearlyDone(count=2,kind='s') +
                                      getFeaturedThenNearlyDone(count=2,kind='p'))
              }]))

def team(request):
    '''
    about the givology team, not giving teams
    '''
    return teamspecific(request, None)
def teamspecific(request, name):
    return render_to_response(tloc+'team.html', dictcombine(
            [maindict(request),
             {'choice0':'About',
              'name':name,
              }]))

class mock_captcha_result:
    def is_valid(self):
        return True

def handle_donor_submission(form, request):
    asdf = request.POST.get('asdf')
    spammed = asdf is not None and len(asdf) > 0
    if islive:
        captcha_result = captcha.check_captcha(request)
    else:
        captcha_result = mock_captcha_result()

    form.apply(request.POST)
    v=form.verify()
    if v and not spammed and captcha_result is not None and captcha_result.is_valid:
        dict=form.retrieve()
        if not is_valid_username(dict['username']):
            print 'not alnum'
            return (True, django.http.HttpResponse(
                'Usernames must be only letters and numbers'))
        if User.objects.filter(
            username=dict['username']).count() != 0:
            return True, django.http.HttpResponse(
                dict['username'] + ' already exists')
        if not isemailvalid(dict['email']):
            return True, django.http.HttpResponse(
                'email address looks invalid...')
        #hash password now, so that it's never sent raw.
        dict['password'] = hashpassword(dict['password'])

        msg = pickle.dumps(dict)
        mac = hmac.new(hmac_key, msg).digest()
        code = urlsafe_b64encode(msg + mac)
        link = 'https://www.givology.org/account/confirm/?code=%s' % code
        fr = 'Givology <no-reply@givology.org>'
        to = dict['email']
        subject = 'Givology Account Confirmation'
        body = _("Hello %(name)s,\n\nComplete your Givology registration by following this link:\n\n%(link)s\n\n Givology") % {'name':dict['name'], 'link':link}
        htmlbody = render_to_string(tloc+'confirmationemail',
                                    {'name':dict['name'],
                                     'link':link})
        print 'for localhost usage, the link is http://localhost:8000/account/confirm/?code=%s' % code
        if islive:
            sendmail(fr, to, subject, body, htmlbody=htmlbody)
        v = True
    if (v or spammed) and captcha_result is not None and captcha_result.is_valid:
        return (True, django.http.HttpResponse('Thank you for registering. Please check your email for a confirmation link.' ))
    if islive:
        return (False, captcha_result)
    else:
        return (False, None)

def newdonor(request):
    form=uform.newdonorform(request)
    v=False
    captcha_result = None
    if request.method=='POST':
        print 'newdonor POST'
        res, html = handle_donor_submission(form, request)
        if res:
            return html
        captcha_result = html
    captcha_html = captcha.new_captcha_html(captcha_result)
    return render_to_response(tloc+'newdonor',dictcombine(
            [maindict(request),
             {'title':'Givology: Register',
              'choice0':'Community',
              'form':form.renderhtml(),
              'captcha_html':captcha_html,
              }]))

def confirmnewdonor(request):
    dcode = None
    msg = None
    mac = None
    try:
        dcode = urlsafe_b64decode(request.GET['code'])
        msg = dcode[:-16]
        mac = hmac.new(hmac_key, msg).digest()
        if mac != dcode[-16:]:
            raise hell
    except:
        logvisit('confirmnewdonor - invalid', request)
        return django.http.HttpResponse('Invalid confirmation link.')

    dict = pickle.loads(msg)

    if (User.objects.filter(
            username=dict['username']).count() != 0 or
        dict['username'] == 'donorbot'):
        logvisit('confirmnewdonor - already', request)
        return render_to_response(
            tloc+'redirect',
            {'destination':'/login/',
             'mesg':'Account already confirmed. Sending you to login!'
             })
    if banned_emails.get(dict['email'],False):
        return django.http.HttpResponse('an error has occured')
    u = User.objects.create_user(
        username=dict['username'],
        email=dict['email'],
        password=dict['password'])
    #to make sure that it doesn't run the hash again...
    u.password=dict['password']
    u.save()
    p = UserProfile(user=u,
                    name=dict['name'],
                    kind='d')
    p.save()
    set_attr('isanon','f',p)
    d = Donor(profile=p)
    d.save()
    logvisit('confirmnewdonor - valid', request)
    return render_to_response(
        tloc+'redirect',
        {'destination':'/login/',
         'mesg':'Donor account confirmed. Sending you to login!'
         })

def addstudent(request):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    form = None
    studentadded=False
    studentun = None
    studentname = None
    if (user.is_staff or
          user.get_profile().kind == 'o'):
        form = uform.addstudentform(request)
    else:
        return django.http.HttpResponse('no entry!')
    if request.method == 'POST':
        form.apply(request.POST)
        if form.verify():
            dict = form.retrieve()
            un=''
            name = dict['name']
            if len(dict['fname'])>1:
                name += ' ('+dict['fname']+')'
            if 'username' in dict:
                un = dict['username']
            else: #create a username
                for i in xrange(10000000):
                    un=name2username(name, i)
                    if User.objects.filter(
                        username=un).count() == 0:
                        break
            pw=''
            if 'password' in dict:
                pw = dict['password']
            else:
                pw = User.objects.make_random_password()
            u = User.objects.create_user(
                username=un,
                email='none',
                password=pw)
            u.save()
            bdate = None
            try:
                bdate = datetime.datetime.strptime(dict['created'],'%Y&ndash;%m&ndash;%d')
            except:
                bdate = datetime.datetime.strptime(dict['created'],'%Y-%m-%d')
            p = UserProfile(
                user=u,
                gender=dict['gender'],
                created=bdate,
                kind='s',
                name=name)
            p.save()
            o = Organization.objects.get(
                id=int(dict['org']))
            r = Recipient(
                profile=p,
                org=o,
                approved=user.is_staff,
                postneedapproval=True)
            r.save()
            g = Grant(
                rec=r,
                want=int(dict['want_0']))
            g.save()
            form.set_attrs(p)
            [f for f in form.subforms
             if f.label=='Grant Information #(0)'][0].set_attrs(g)
            form.todefault()
            studentadded=True
            studentun=un
            studentname=dict['name']
        else:
            pass
    return render_to_response(tloc+'addstudent', dictcombine(
            [maindict(request),
             {'title':'Givology: Add Students',
              'choice0':'My Account',
              'form':form.renderhtml(),
              'studentadded':studentadded,
              'studentun':studentun,
              'studentname':studentname,
              }]))

def addproject(request):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    form = None
    studentadded=False
    studentun = None
    studentname = None
    if (user.is_staff or
          user.get_profile().kind == 'o'):
        form = uform.addprojectform(request)
    else:
        return django.http.HttpResponse('no entry!')
    if request.method == 'POST':
        form.apply(request.POST)
        if form.verify():
            dict = form.retrieve()
            un=''
            name = dict['name']
            if len(dict['fname'])>1:
                name += ' ('+dict['fname']+')'
            if 'username' in dict:
                un = dict['username']
            else: #create a username
                for i in xrange(10000000):
                    un=name2username(name, i)
                    if User.objects.filter(
                        username=un).count() == 0:
                        break
            pw=''
            if 'password' in dict:
                pw = dict['password']
            else:
                pw = User.objects.make_random_password()
            u = User.objects.create_user(
                username=un,
                email='none',
                password=pw)
            u.save()
            p = UserProfile(
                user=u,
                kind='p',
                name=name)
            p.save()
            o = Organization.objects.get(
                id=int(dict['org']))
            r = Recipient(
                profile=p,
                org=o,
                approved=user.is_staff,
                postneedapproval=True)
            r.save()
            g = Grant(
                rec=r,
                want=int(dict['want_0']))
            g.save()
            form.set_attrs(p)
            [f for f in form.subforms
             if f.label=='Grant Information #(0)'][0].set_attrs(g)
            form.todefault()
            studentadded=True
            studentun=un
            studentname=name
        else:
            pass
    return render_to_response(tloc+'addproject', dictcombine(
            [maindict(request),
             {'title':'Givology: Add Projects',
              'choice0':'My Account',
              'form':form.renderhtml(),
              'studentadded':studentadded,
              'studentun':studentun,
              'studentname':studentname,
              }]))

def addorganization(request):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    form = None
    studentadded=False
    studentun = None
    studentname = None
    if user.is_staff:
        form = uform.addorganizationform(request)
    else:
        return django.http.HttpResponse('no entry!')
    if request.method == 'POST':
        form.apply(request.POST)
        if form.verify():
            dict = form.retrieve()
            un=''
            name = dict['name']
            if 'username' in dict:
                un = dict['username']
            else: #create a username
                for i in xrange(10000000):
                    un=name2username(name, i)
                    if User.objects.filter(
                        username=un).count() == 0:
                        break
            pw=''
            if 'password' in dict:
                pw = dict['password']
            else:
                pw = User.objects.make_random_password()
            u = User.objects.create_user(
                username=un,
                email='none',
                password=pw)
            u.save()
            p = UserProfile(
                user=u,
                kind='o',
                name=name)
            p.save()
            o = Organization(
                profile=p)
            o.save()
            form.set_attrs(p)
            form.todefault()
            studentadded=True
            studentun=un
            studentname=name
        else:
            pass
    return render_to_response(tloc+'addorganization', dictcombine(
            [maindict(request),
             {'title':'Givology: Add Partners',
              'choice0':'My Account',
              'form':form.renderhtml(),
              'studentadded':studentadded,
              'studentun':studentun,
              'studentname':studentname,
              }]))

def approve(request):
    unapproved = Recipient.objects.filter(approved=False)
    posts = BlogPost.objects.filter(approved=False)
    return render_to_response(tloc+'approve', dictcombine(
            [maindict(request),
             {'user':apparent_user(request),
              'title':'Givology: Approve Recipients',
              'navbar':navbar(apparent_user(request)),
              'recipients':unapproved,
              'posts':posts,
              }]))



# Lightmaker's "landing pages"
def whoweare(request):
    return render_to_response(tloc+'who-we-are.html', dictcombine(
        [maindict(request),
         {'title':'Givology: About',
          'choice0': 'who-we-are',
          'choice1': '',
          }]))
def howitworks(request):
    return render_to_response(tloc+'how-it-works.html', dictcombine(
        [maindict(request),
         {'title':'Givology: How it Works',
          'impact':getimpactthisweek(),
          'choice0': 'who-we-are',
          'choice1': 'how-it-works',
          }]))
def missionvision(request):
    return render_to_response(tloc+'mission-vision.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Mission & Vision',
          'impact':getimpactthisweek(),
          'choice0': 'who-we-are',
          'choice1': 'mission-vision',
          }]))
def boardofdirectors(request):
    return render_to_response(tloc+'board-of-directors.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Board of Directors',
          'choice0': 'who-we-are',
          'choice1': 'board-of-directors',
          }]))
def executiveteam(request):
    return render_to_response(tloc+'executive-team.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Executive Team',
          'choice0': 'who-we-are',
          'choice1': 'executive-team',
          }]))
def partnerships(request):
    return render_to_response(tloc+'partnerships.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Partnerships',
          'choice0': 'who-we-are',
          'choice1': 'partnerships',
          }]))
def faq(request):
    return render_to_response(tloc+'faq.html', dictcombine(
        [maindict(request),
         {'title':'Givology: FAQ',
          'choice0': 'who-we-are',
          'choice1': 'faq',
          }]))
def contactus(request):
    messagesent=False
    if 'message' in request.POST:
        fr = ''
        if 'from' in request.POST:
            fr = request.POST['from']
        subject = ''
        try:
            subject = request.POST['subject']
            assert len(subject) > 0
        except:
            subject = 'No Subject'
        email = ''
        try:
            email = request.POST['email']
            assert len(email) > 4
        except:
            email = 'No email given'

        #possible anti-spam?
        if request.POST['reason'] != '':
            return django.http.HttpResponse('Thank you for your message!')

        msg = request.POST['message']
        msg = tagclean(msg)
        msg = stripshow(msg)
        subject = 'Givology Contact Message: '+subject
        body = '\nMessage from Contact Us page from %s, %s\n\n%s\n\n' % (fr, email, msg)
        print subject
        print body
        send_message(fr=User.objects.get(username='givbot'),
                     to=[a.username for a in User.objects.filter(is_staff=True)],
                     subject=subject,
                     body=body)
        #sendmail(
        #    fr='giv_updates@givology.org',
        #    to='info@givology.org',
        #    subject=subject,
        #    body= body,
        #    )
        messagesent=True
    return render_to_response(tloc+'contact-us.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Contact Us',
          'messagesent': messagesent,
          'tinymce' : False,
          'choice0': 'who-we-are',
          'choice1': 'contact-us',
          }]))
def ourcommunity(request):
    return render_to_response(tloc+'our-community.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Our Community',
          'choice0': 'our-community',
          }]))
def ourdonors(request):
    return render_to_response(tloc+'our-donors.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Our Donors',
          'newdonors':getnewdonors(),
          'newdonations' : getnewdonations(),
          'choice0': 'our-community',
          'choice1': 'our-donors',
          }]))
def fieldpartners(request):
    return render_to_response(tloc+'field-partners.html', dictcombine(
        [maindict(request),
         organizationsearch(request),
         {'title':'Givology: Field Partners',
          'choice0': 'our-community',
          'choice1': 'field-partners',
          }]))
def givingteams(request):
    return render_to_response(tloc+'giving-teams.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Giving Teams',
          'choice0': 'our-community',
          'choice1': 'giving-teams',
          }]))
def givnow(request):
    return render_to_response(tloc+'giv-now.html', dictcombine(
        [maindict(request),
         {'title':'Givology: GIV Now',
          'choice0': 'giv-now',
          }]))
def givstudents(request):
    d = searchrecipients(request, 's')
    return render_to_response(tloc+'giv-students.html', dictcombine(
        [maindict(request),
         d,
         {'title':'Givology: Students',
          'featured_recipients': getFeaturedThenNearlyDone(count=4,kind='s'),
          'feature_kind':'Students',
          'choice0': 'giv-now',
          'choice1': 'giv-students'
          }]))
def givprojects(request):
    d = searchrecipients(request, 'p')
    return render_to_response(tloc+'giv-projects.html', dictcombine(
        [maindict(request),
         d,
         {'title':'Givology: Projects',
          'featured_recipients':getFeaturedThenNearlyDone(count=4, kind='p'),
          'feature_kind':'Projects',
          'choice0': 'giv-now',
          'choice1': 'giv-projects'
          }]))
def givgivology(request):
    braintree_error = None
    if request.POST:
        quantity = int(request.POST['quantity'])
        print quantity
        result = braintree.Transaction.sale({
            "amount": str(quantity) + ".00",
            "credit_card": {
                "number": request.POST["number"],
                "cvv": request.POST["cvv"],
                "expiration_month": request.POST["month"],
                "expiration_year": request.POST["year"]
                },	
            "customer": {
                "first_name": request.POST["firstname"],
                "last_name": request.POST["lastname"],
                "email": request.POST["email"]
                },
            "billing": {
                "postal_code": request.POST["zip"],
		"country_code_alpha2": request.POST["country"]
                },
            "options": {
                "submit_for_settlement": True
                },
	    "tax_exempt": True
            })
        if result.is_success:
            print 'success!'
            return render_to_response(tloc+'redirect', {
                'mesg' : 'Transaction for $' + str(quantity) + ' submitted! Thank you!',
                'destination':'/'})
        else:
            braintree_error = result.message
    return render_to_response(tloc+'giv-givology.html', dictcombine(
        [maindict(request),
         {'title':'Givology: GIV to Us',
          'impact':getimpactthisweek(),
          'braintree_error' : braintree_error,
          'braintree_client_side_encryption_key' : braintree_client_side_encryption_key,
          'choice0': 'giv-now',
          'choice1': 'giv-givology'
          }]))

#def giftcertificates(request):
#    return render_to_response(tloc+'gift-certificates.html', dictcombine(
#        [maindict(request),
#         {'title':'Givology: Gift Certificates',
#          'choice0': 'giv-now',
#          'choice1': 'gift-certificates'
#          }]))
def getinvolved(request):
    return render_to_response(tloc+'get-involved.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Get Involved',
          'choice0': 'get-involved',
          }]))
def startchapter(request):
    return render_to_response(tloc+'start-chapter.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Start a Chapter',
          'choice0': 'get-involved',
          'choice1': 'start-chapter',
          }]))
def volunteer(request):
    return render_to_response(tloc+'volunteer.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Volunteer',
          'choice0': 'get-involved',
          'choice1': 'volunteer',
          }]))
def internships(request):
    return render_to_response(tloc+'internships.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Internships',
          'choice0': 'get-involved',
          'choice1': 'internships',
          }]))
def fellowships(request):
    return render_to_response(tloc+'fellowships.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Fellowships',
          'choice0': 'get-involved',
          'choice1': 'fellowships',
          }]))
def spreadtheword(request):
    return render_to_response(tloc+'spread-the-word.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Spread the Word',
          'impact':getimpactthisweek(),
          'numdonors' : formnum(Donor.objects.all().count()),
          'choice0': 'get-involved',
          'choice1': 'spread-the-word',
          }]))
def _blogs_helper(request, choice_dict, base_url, uname=None, selected_encoded_tag = None,
                  author_kind = None, header_override=None, show_tag=True):
    posts = blogpostfilter(request, username=uname)
    posts = posts.filter(iscomment=False)

    if (author_kind is not None):
        posts = posts.filter(author__userprofile__kind = author_kind)

    ids = []
    if 'ids' in request.GET:
        try:
            ids = [int(x) for x in string.split(request.GET['ids'], '-')]
        except:
            ids = []

    if len(ids) > 0:
        last_id = ids[-1]
        posts = posts.filter(id__lt = last_id)

    tag_filtering_enabled = selected_encoded_tag is not None

    if tag_filtering_enabled:
        selected_tag = re.sub('--', '-',
                              re.sub(r'([^-])-([^-])', r'\1 \2', selected_encoded_tag))
    else:
        selected_tag = None

    if tag_filtering_enabled:
        posts = posts.filter(tags__tag=selected_tag)
    
    # max_num_tags = 20
    # top_tags = top_tags[0:min(max_num_tags, len(top_tags))]

    posts = posts[:11]
    
    blog          = paginate(request, posts)
    blog['posts'] = [p.dicttorender() for p in blog['objects']]

    if len(ids) > 0:
        prev_ids = ids[:-1]
        blog['get_prev'] = True
        blog['prev_ids'] = string.join([str(x) for x in prev_ids], '-')
    else:
        blog['get_prev'] = False

    if (len(posts) == 11):
        next_ids = ids[:]
        next_ids.append(min([int(b['id']) for b in blog['posts']]))
        blog['get_next'] = True
        blog['next_ids'] = string.join([str(x) for x in next_ids], '-')
    else:
        blog['get_next'] = False
        
    name = None
    if uname is not None:
        name = User.objects.get(username=uname).get_profile().name
    else:
        name = 'Givology'

    return render_to_response(tloc+'blogs.html', dictcombine(
        [maindict(request),
         {'title': header_override,
          'blog': blog,
          'impact':getimpactthisweek(),
          'numdonors' : formnum(Donor.objects.all().count()),
          'uname': uname,
          'name': name,
          #'top_tags': top_tags,
          'selected_tag': selected_tag,
          'header_override': header_override,
          'show_tag': show_tag,
          },
         choice_dict]))

def blogs(request, base_url='blogs/', uname=None, selected_encoded_tag=None):
    if selected_encoded_tag is None and uname is None:
        selected_encoded_tag = 'givology-news'
    choice1s = [{ 'uname': uname, 'name': user.get_profile().name, }
                for user in User.objects.filter(username=uname)]
    if uname is not None and User.objects.filter(username=uname).count() < 1:
        return django.http.HttpResponseNotFound('Username not found')
    return _blogs_helper(request,
                         choice_dict = { 'choice0': 'blogs',
                                         'choice1': fif(uname is None, 'givology-blog', ''),
                                         'choice1s': choice1s, },
                         #url = '/blogs/',
                         header_override = 'Givology: Blogs',
                         show_tag = (not (uname is None and selected_encoded_tag == 'givology-news')),
                         uname = uname,
                         base_url = base_url,
                         selected_encoded_tag = selected_encoded_tag);

def field_blogs(request, base_url='blogs/', uname=None, selected_encoded_tag='notes-from-the-field'):
    return _blogs_helper(request,
                         choice_dict = { 'choice0': 'blogs',
                                         'choice1': fif(uname is None, 'givology-blog-notes', ''),
                                         'choice1s': [], },
                         header_override = 'Givology: Notes From the Field',
                         show_tag =  (selected_encoded_tag != 'notes-from-the-field'),
                         #url = '/blogs/',
                         base_url = base_url,
                         selected_encoded_tag = selected_encoded_tag);

def student_blogs(request, base_url='blogs/', uname=None, selected_encoded_tag=None):
    return _blogs_helper(request,
                         choice_dict = { 'choice0': 'blogs',
                                         'choice1': 'givology-blog-students',
                                         'choice1s': [], },
                         header_override = 'Givology: Student Blogs',
                         author_kind = 's',
                         base_url = base_url,
                         selected_encoded_tag = selected_encoded_tag);


def project_blogs(request, base_url='blogs/', uname=None, selected_encoded_tag=None):
    return _blogs_helper(request,
                         choice_dict = { 'choice0': 'blogs',
                                         'choice1': 'givology-blog-projects',
                                         'choice1s': [], },
                         header_override = 'Givology: Project Blogs',
                         author_kind = 'p',
                         uname = uname,
                         base_url = base_url,
                         selected_encoded_tag = selected_encoded_tag);


def media(request):
    return render_to_response(tloc+'media.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Media',
          'choice0': 'media',
          }]))
def photos(request):
    return render_to_response(tloc+'photos.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Photos',
          'choice0': 'media',
          'choice1': 'photos',
          }]))
def videos(request):
    return render_to_response(tloc+'videos.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Videos',
          'choice0': 'media',
          'choice1': 'videos'
          }]))
def press(request):
    return render_to_response(tloc+'press.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Press',
          'impact':getimpactthisweek(),
          'choice0': 'media',
          'choice1': 'press'
          }]))
def annualreports(request):
    return render_to_response(tloc+'annual-reports.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Annual Reports',
          'impact':getimpactthisweek(),
          'choice0': 'media',
          'choice1': 'annual-reports'
          }]))
def shop(request):
    return render_to_response(tloc+'shop.html', dictcombine(
        [maindict(request),
         {'title':'Givology: Shop',
          'choice0': 'shop',
          }]))



def vision(request):
    '''
    'our vision' page
    '''
    return render_to_response(tloc+'vision', dictcombine(
                    [maindict(request),
                     {'title':'Givology: Vision',
                      'choice0': 'About',
                      }]))
def partners(request):
    return partnersspecific(request, None)
def partnersspecific(request, name):
    return render_to_response(tloc+'partners', dictcombine(
            [maindict(request),
             {'title'  : 'Givology: Partners',
              'choice0': 'Community',
              'choice1': 'Partners',
              'name'   : name,
              }]))

#####################################
# NOTE: These are some old pages which need to be redirected to the new pages
def donate(request):
    return render_to_response(tloc+'redirect', {'destination':'/giv-now/'})
def donateffstudents(request):
    return render_to_response(tloc+'redirect', {'destination':'/giv-now/giv-students/'})
def donatestudents(request, ff=False):
    return render_to_response(tloc+'redirect', {'destination':'/giv-now/giv-students/'})
def donateffprojects(request):
    return render_to_response(tloc+'redirect', {'destination':'/giv-now/giv-projects/'})
def donateprojects(request, ff=False):
    return render_to_response(tloc+'redirect', {'destination':'/giv-now/giv-projects/'})
#####################################

def searchrecipients(request, kind, ff=False):
    '''
    search page for recipients to donate to.

    todo: replace the from giv_grant g with a query returning a table of just the most recent grants for each recipient...
    '''
    assert kind in ['s','p']
    offset = None
    try:
        offset = int(request.GET['offset'])
        assert offset >= 0
    except: offset = 0
    count = None
    try:
        count  = int(request.GET['count'])
        assert count >= 1
    except: count = 10

    getopts = []

    froms = ['giv_recipient r',
             'giv_userprofile p',
             'giv_grant g']
    wheres = ['p.id=r.profile_id',
              'p.kind="%s"'%(kind),
              'g.rec_id=r.id',
              'not exists (select * from giv_grant g2 where g2.created > g.created and g.rec_id = g2.rec_id)']
    values = []
    orderby = ' ((g.percent_very_informal + 1) %% 101) desc'


    if not canviewunapproved(request):
        wheres.append('r.approved=1')

    #name stuff
    name = ''
    if 'name' in request.GET:
        name = request.GET['name']
    if len(name) > 0:
        getopts+=['name=%s'%(name)]
        names = name.strip().split(' ')
        for n in names:
            if DATABASE_ENGINE == 'sqlite3':
                wheres.append('p.name glob ?')
                values.append('*'+n+'*')
            else:
                wheres.append('p.name regexp ?')
                values.append('.*'+n+'.*')

    # age stuff
    agegroups = ['0-5',
                 '6-10',
                 '11-15',
                 '16-']
    agegroup = ''
    if 'agegroup' in request.GET:
        agegroup = request.GET['agegroup']
        if agegroup not in agegroups:
            agegroup = ''
    if len(agegroup) > 0:
        getopts+=['agegroup=%s'%(agegroup)]
        minage, maxage = {
            '0-5':(0,5),'6-10':(5,10),
            '11-15':(10,15),'16-':(15,1000)}[agegroup]
        today = datetime.datetime.today()
        try:
            maxcr = str(today.replace(year=today.year-minage))
        except:
            maxcr = str(today.replace(year=today.year-minage, day=28))
        try:
            mincr = str(today.replace(year=today.year-maxage))
        except:
            mincr = str(today.replace(year=today.year-maxage, day=28))
        wheres.append("p.created >= '%s'"%(mincr))
        wheres.append("p.created <= '%s'"%(maxcr))

    # education level stuff
    edutypes = ['Primary School',
                'Middle School',
                'High School',
                'University']
    edulevel = ''
    if 'edulevel' in request.GET:
        edulevel = request.GET['edulevel']
        if edulevel not in edutypes:
            edulevel = ''
    if len(edulevel) > 0:
        getopts+=['edulevel=%s'%(edulevel)]
        froms.append('giv_attrib ake')
        froms.append('giv_attrval ave')
        wheres.append('ake.name="edutype"')
        wheres.append('ake.id=ave.attr_id')
        wheres.append('ave.oid=p.id')
        wheres.append('ave.tablename="giv_userprofile"')
        wheres.append('ave.val="%s"'%(
                {'Primary School':'primary',
                 'Middle School':'middle',
                 'High School':'high',
                 'University':'university',
                 }[edulevel]))

    # gender stuff
    genders = ['Male','Female']
    gender = ''
    if 'gender' in request.GET:
        gender = request.GET['gender']
        if gender not in genders:
            gender = ''
    if len(gender) > 0:
        getopts+=['gender=%s'%(gender)]
        wheres.append('p.gender="%c"'%(
                {'Male':'m','Female':'f'}[gender]))

    # country stuff
    country = ''
    countries = [x for x in get_countries(kind=kind) if x and len(x) >= 2]
    if 'country' in request.GET:
        country = request.GET['country']
        if country not in countries:
            country = ''
    if len(country) > 0:
        getopts+=['country=%s'%(country)]
        froms.append('giv_attrib akc')
        froms.append('giv_attrval avc')
        wheres.append('akc.name="country"')
        wheres.append('akc.id=avc.attr_id')
        wheres.append('avc.oid=p.id')
        wheres.append('avc.tablename="giv_userprofile"')
        wheres.append('avc.val=?')
        values.append(country)

    # province stuff
    province = ''
    provinces = [x for x in get_provinces(
        country=fif(len(country)>0,country,None),
        kind=kind) if x and len(x) >= 2]
    if 'province' in request.GET:
        province = request.GET['province']
        if province not in provinces:
            province = ''
    if len(province) > 0:
        getopts+=['province=%s'%(province)]
        froms.append('giv_attrib akp')
        froms.append('giv_attrval avp')
        wheres.append('akp.name="province"')
        wheres.append('akp.id=avp.attr_id')
        wheres.append('avp.oid=p.id')
        wheres.append('avp.tablename="giv_userprofile"')
        wheres.append('avp.val=?')
        values.append(province)

    # partner stuff
    partners = [p.name for p in UserProfile.objects.filter(kind='o').order_by('name')]
    partner = ''
    if 'partner' in request.GET:
        partner = request.GET['partner']
        if partner not in partners:
            partner = ''
    if len(partner) > 0:
        getopts+=['partner=%s'%(partner)]
        froms.append('giv_organization po')
        froms.append('giv_userprofile pp')
        wheres.append('pp.id=po.profile_id')
        wheres.append('pp.name=?')
        values.append(partner)
        wheres.append('po.id=r.org_id')
        partners.remove(partner)
        partners = [partner]+partners

    # percent funded stuff
    completion = ''
    if ff: completions = None
    else: completions = ['100','90-99','70-89','50-69',
                         '25-49','0-25']
    if 'completion' in request.GET:
        completion = request.GET['completion']
        if completion not in completions:
            completion = ''
        if completion == '100':
            ff = True
    if len(completion) > 0:
        getopts+=['completion=%s'%(completion)]
        #note that if completion == '100', ff <- true
        lo, hi = {0:(100,100),1:(90,99),2:(70,89),
                  3:(50,69),4:(25,49),
                  5:(0,25)}[completions.index(completion)]
        wheres.append('g.percent_very_informal <= %d'%hi)
        wheres.append('g.percent_very_informal >= %d'%lo)

    #select which kind of grant status to filter by
    #if ff: wheres.append('g.left_very_informal <= 0')
    #else:  wheres.append('g.left_very_informal > 0')

    # pagination
    page = 1
    if 'page' in request.GET:
        page = int(request.GET['page'])
    limit = 15
    offset = (page - 1) * limit


    # the query!
    query = mkquery('distinct r.id', froms, wheres, orderby, offset, limit)
    nquery= mkquery('count(distinct r.id)', froms, wheres)
    cursor = connection.cursor()
    cursor.execute(nquery, values)
    num_hits = int(cursor.fetchone()[0])
    cursor.execute(query, values)
    #if offset > 0:
    #    cursor.fetchmany(offset)
    recs = []
    for i in xrange(limit):
        try: recs.append(Recipient.objects.get(id=int(cursor.fetchone()[0])))
        except: break
    recs = [rec.profile.summary(apparent_user(request)) for rec in recs]

    # page links
    page_links = []
    for i in xrange(int(math.ceil(num_hits*1.0/limit))):
        page_links += [{'page_num' : i + 1,
                        'url' : '.?'+'&'.join(getopts + ['page=%i'%(i+1)])}]
    next_page_link = '.?'+'&'.join(getopts+['page=%i'%(page+1)])
    prev_page_link = '.?'+'&'.join(getopts+['page=%i'%(page-1)])
    if page <= 1: prev_page_link = False
    if page >= len(page_links): next_page_link = False
    return {'results':recs,
            'name':name,
            'kind':kind,
            'agegroup':agegroup,
            'agegroups':agegroups,
            'edulevel':edulevel,
            'edulevels':edutypes,
            'gender':gender,
            'genders':genders,
            'completion':completion,
            'completions':completions,
            'province':province,
            'provinces':provinces,
            'country':country,
            'countries':countries,
            'partner':partner,
            'partners':partners,
            'page':page,
            'count':count,
            'numresults':num_hits,
            'numshown':len(recs),
            'getopts':'&'.join(getopts),
            'is_paginated':num_hits != len(recs),
            'page_links' : page_links,
            'next_page_link' : next_page_link,
            'prev_page_link' : prev_page_link,
            }

def donaterecipient(request, kind, ff=False):
    d = searchrecipients(request, kind, ff)
    return render_to_response(
        tloc+'donate' + {'s':'students','p':'projects'}[kind],
        dictcombine(
            [maindict(request),
             d,
             {'title':'Givology: Donate',
              'choice0': 'Give',
              'choice1': 'Students'}
              ]))

def organizationsearch(request):

    getopts = []

    froms = ['giv_organization o',
             'giv_userprofile p']
    wheres = ['p.id=o.profile_id',
              'p.kind="o"']
    values = []
    orderby = 'p.name'

    #name stuff
    name = ''
    if 'name' in request.GET:
        name = request.GET['name']
    if len(name) > 0:
        getopts+=['name=%s'%(name)]
        names = name.strip().split(' ')
        for n in names:
            if DATABASE_ENGINE == 'sqlite3':
                wheres.append('p.name glob ?')
                values.append('*'+n+'*')
            else:
                wheres.append('p.name regexp ?')
                values.append('.*'+n+'.*')

    # status stuff
    statuses = uform.PARTNER_STATES
    pstatus = ''
    if 'pstatus' in request.GET:
        pstatus = request.GET['pstatus']
        if pstatus not in statuses:
            pstatus = ''
    #if len(pstatus) > 0:
    for i in xrange(1):
        getopts+=['pstatus=%s'%(pstatus)]
        froms.append('giv_attrib aks')
        froms.append('giv_attrval avs')
        wheres.append('aks.name="pstatus"')
        wheres.append('aks.id=avs.attr_id')
        wheres.append('avs.oid=p.id')
        wheres.append('avs.tablename="giv_userprofile"')
        if len(pstatus) > 0:
            wheres.append('avs.val="%s"'%(pstatus))
        else:
            wheres.append('avs.val<>"Cancelled"')

    # the query!
    query = mkquery('distinct o.id',froms,wheres,orderby)
    nquery= mkquery('count(distinct o.id)',froms,wheres)
    cursor = connection.cursor()
    cursor.execute(nquery, values)
    total = int(cursor.fetchone()[0])
    cursor.execute(query, values)
    orgs = []
    for i in xrange(total):
        try: orgs.append(Organization.objects.get(id=int(cursor.fetchone()[0])))
        except: break
    orgs = [org.profile.summary(apparent_user(request)) for org in orgs]

    getopts = '&'.join(getopts)

    return {'results': orgs,
            'name':name,
            'pstatus':pstatus,
            'statuses':statuses,
            'getopts':getopts,
            'partner_count': total,
            'total_partner_count': Organization.objects.all().count(),
            }

def donoraccount(request, user):
    import time
    print time.clock()
    un = user.username
    profile = user.get_profile()
    obj = profile.get_object()
    donor = obj
    if not isinstance(donor, Donor):
        return django.http.HttpResponseNotFound('This page is for donors only.')

    weekago=(datetime.datetime.now() - datetime.timedelta(days=7))
    #todo: need to make sure that the impactthisweek works on situation where a recipient has received from multiple sources in one week and make sure this doesn't double count it, or count students that weren't donated to by this person.
    print time.clock()
    '''
    impactthisweek = {
        'title'   : 'Impact this week',
        'dollars' : sumpg(createdafter=weekago, donor=obj),
        'npayments' : Paymenttogrant.objects.filter(
            created__gt=weekago, donor=obj).count(),
        'studs' : Recipient.objects.filter(
            grant_set__paymenttogrant_set__created__gt=weekago,
            grant_set__paymenttogrant_set__donor=obj).filter(
            profile__kind='s').distinct().count(),
        'projs' : Recipient.objects.filter(
            grant_set__paymenttogrant_set__created__gt=weekago,
            grant_set__paymenttogrant_set__donor=obj).filter(
            profile__kind='p').distinct().count(),
        }
    '''
    print time.clock()
    impactoverall = {
        'title'   : 'Impact this week',
        'dollars' : sumpg(donor=obj),
        'npayments' : Paymenttogrant.objects.filter(donor=obj).count(),
        'studs' : Recipient.objects.filter(
            grant_set__paymenttogrant_set__donor=obj).filter(
            profile__kind='s').distinct().count(),
        'projs' : Recipient.objects.filter(
            grant_set__paymenttogrant_set__donor=obj).filter(
            profile__kind='p').distinct().count(),
        }
    print 'about to get updates; '+str(time.clock())
    newblogs = [{'authorimg':p.author.get_profile().get_image_url(50,50),
                 'authoruname':p.author.username,
                 'authorname':p.author.get_profile().name,
                 'subject':takestr(100,p.subject),
                 'pid':p.id,
                 'url':p.url(),
                 }
                for p in (take(4, profile.get_updates(
                    ).order_by('-created')))
                ]
    '''
    #misc stat chart stuff
    donationlist = Paymenttogrant.objects.filter(donor=obj).order_by('-created')
    donationCountries = {}
    donationPartners = {}
    for d in donationlist:
        g = d.grant
        r = g.rec
        country = get_attr('country',r.profile,'No Country')
        donationCountries[country] = donationCountries.get(country,0)+d.amount
        pid = r.org.id
        donationPartners[pid] = donationPartners.get(pid,0)+d.amount
    donationCountries = [{'country':country,
                          'amount':amt}
                         for (country,amt) in
                         sorted(donationCountries.items(),
                                lambda a, b: int(a[1]-b[1]))]
    donationPartners = [{'amount':amt,
                         'pid':pid,
                         'partner':Organization.objects.get(id=pid)}
                        for (pid, amt) in
                        sorted(donationPartners.items(),
                               lambda a, b: int(a[1]-b[1]))]

    '''

    print time.clock()
    input = donor.pledged_informal()
    output = donor.donated_informal()
    gcbalance = donor.gift_cert_balance()
    gcsend = donor.gift_cert_out()
    gcrecv = donor.gift_cert_in()
    balance = donor.have_informal()

    print 'got output, balance, input; '+str(time.clock())

    pgs = list(Paymenttogrant.objects.filter(
        donor=obj).order_by('-created'))

    recs =[Recipient.objects.get(id=i)
           for i in xremoveduplicates(
            pg.grant.rec.id for pg
            in pgs)
           ]
    print time.clock()

    recs = [r.profile.summary() for r in recs]
    for rec in recs:
        rec['messageme']=True
        rec['my_given'] = sum(
            [pg.amount for pg in pgs if pg.grant.rec.id == rec['obj_id']])
        rec['my_given_percent'] = int((100.0*rec['my_given']) / rec['grant_have_total'])

    print time.clock()

    volunteerworks = list(VolunteerWork.objects.filter(volunteer=user).order_by('-when'))
    volunteer_total_minutes = sum([vw.minutes for vw in volunteerworks])
    volunteer_total_hours = (volunteer_total_minutes / 60 +
                             fif(volunteer_total_minutes % 60 > 0, 1, 0))

    r = render_to_response('account.html', dictcombine(
            [maindict(request),
             {'title':'Givology: Account',
              'choice0': 'dashboard',
              'choice1': 'account',
              # 'impact':impactthisweek,
              'impacto':impactoverall,
              'feedurl':'rss.xml',
              'isstaff':user.is_staff,
              'havegc' : GiftCert.objects.filter(creator=obj).count() + GiftCert.objects.filter(receiver=obj).count() > 0,
              'input'  :input,
              'output' :output,
              'gcbalance':gcbalance,
              'gcsend':gcsend,
              'gcrecv':gcrecv,
              'balance':balance,
              'posbalance':balance>0,
              'negbalance':balance<0,
              'posoutput':output>0,
              'recs' : recs,
              'summary' : profile.summary(),
              'username':user.username,
              'hasimage':profile.has_image(),
              'newblogs':newblogs,
              'url':profile.url(),
              'volunteerworks':volunteerworks,
              'volunteer_total_hours': volunteer_total_hours,
              'hasvolunteerworks':len(volunteerworks),
              #'donationlist':donationlist,
              #'donationCountries':donationCountries,
              #'donationPartners':donationPartners,
              }]))
    print time.clock()
    return r



def organizationaccount(request):
    user = apparent_user(request)
    un = user.username
    profile = user.get_profile()
    org = profile.get_object()
    recs = org.recipient_set.all()
    studs = org.recipient_set.filter(profile__kind='s')
    projs = org.recipient_set.filter(profile__kind='p')
    return render_to_response(tloc+'accountorg', dictcombine(
                    [maindict(request),
                     {'title':'Givology: Account',
                      'choice0': 'My Account',
                      'choice1': 'My Portfolio',
                      'studs':studs,
                      'projs':projs,
                      'feedurl':'rss.xml',
                      }]))
@reqUser
def account(request, user, profile, obj):
    if user == request.user:
        visit('account', user) #note that we have visited this page
    if isinstance(obj, Donor):
        return donoraccount(request,user)
    if isinstance(obj, Organization):
        return organizationaccount(request)
    return render_to_response(tloc+'account',
           {'user':apparent_user(request),
            'title':'Givology: Account',
            'navbar':navbar(apparent_user(request)),
            'choice0':'My Account',
            'choice1':'My Portfolio',
            'feedurl':'rss.xml',
            })

@reqDonor
def autodonate(request, user, profile, donor):
    amount = None
    try:
        amount = int(request.POST['amount'])
        assert (amount > 0)
    except:
        return django.http.HttpResponse(
            'Need a whole number for the amount to autodonate')
    if amount > donor.have_informal():
        return django.http.HttpResponse('insufficient funds!')

    while amount > 0:
        grants = Grant.objects.filter(left_very_informal__gt=0).order_by('-percent_very_informal')
        count = grants.count()
        if count == 0:
            break
        minimum = (amount / count) + 20
        num = 0
        recs = []
        for grant in grants:
            if amount <= 0 or num >= count:
                break
            subamt = amount/3 #intended to work to spread the donations around more
            if subamt <= minimum:
                subamt = min(minimum, amount)
            if subamt > grant.left_very_informal:
                subamt = grant.left_very_informal
            payGrant(donor, grant, subamt)
            recs.append(grant.rec.profile.summary())
            amount -= subamt
            num += 1

    return render_to_response(tloc+'autodonate', dictcombine(
                    [maindict(request),
                     {'title':'Givology: AutoDonate',
                      'choice0': 'My Account',
                      'choice1': 'AutoDonate',
                      'recs'   : recs,
                      }]))

def wallet(request):
    return render_to_response(tloc+'redirect', {'destination':'/account/#wallet'})
    user = apparent_user(request)
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    donor = apparent_user(request).get_profile().get_object()
    if not isinstance(donor, Donor):
        return django.http.HttpResponseNotFound('This page is for donors only.')
    output = donor.donated_informal()
    balance = donor.have_informal()
    input = balance + output
    return render_to_response(tloc+'wallet', dictcombine(
                    [maindict(request),
                     {'title':'Givology: Wallet',
                      'choice0': 'My Account',
                      'choice1': 'My Wallet',
                      'input'  :input,
                      'output' :output,
                      'balance':balance,
                      'username':user.username,
                      }]))

import proj.giv.gcheckout as gcheckout

def gcheckoutnotification(request):
    #f = '/home/giv/gcheckout'+str(datetime.datetime.today())
    #try:
    #    pickle.dump(request.POST, open(f,'w'), 1)
    #except:
    #    pickle.dump('oh no!', open(f, 'w'), 1)
    return gcheckout.handlenotification(request)

@reqUser
def volunteered(request, user, profile, obj):
    try:
        when = datetime.datetime.now()
        # TODO: Actually get the time from the request
        vw = VolunteerWork(
            volunteer=user,
            minutes=int(request.POST['minutes']),
            action=request.POST['action'],
            when=when)
        vw.save()
        invalidatecache('impactthisweek')
    except:
        # TODO: Add appropriate error response.
        print 'error in volunteered'
        pass
    return render_to_response(tloc+'redirect', {
        'destination':'/blog/'})

@reqDonor
def walletadd(request, user, profile, donor):
    error = None
    braintree_error = None
    try:
        quantity = int(request.POST['quantity'])
        if quantity <= 0:
            error = "Payment to wallet must be greater than zero dollars!"
    except:
        if error is None:
            return render_to_response(tloc+'redirect', {
                    'destination':'/'})
    if 'number' in request.POST:
        result = braintree.Transaction.sale({
            "amount": str(quantity) + ".00",
            "credit_card": {
                "number": request.POST["number"],
                "cvv": request.POST["cvv"],
                "expiration_month": request.POST["month"],
                "expiration_year": request.POST["year"]
                },
            "customer": {
                "first_name": request.POST["firstname"],
                "last_name": request.POST["lastname"],
                "email": request.POST["email"]
                },
            "billing": {
                "postal_code": request.POST["zip"],
		"country_code_alpha2": request.POST["country"]
                },
            "options": {
                "submit_for_settlement": True
                },
	    "tax_exempt": True
            })
        if result.is_success:
            print 'success!'
            pw = Paymenttowallet(
                donor  = donor,
                amount = quantity,
                )
            pw.save()
            return render_to_response(tloc+'redirect', {
                'mesg' : 'Transaction for $' + str(quantity) + ' submitted and added to wallet!',
                'destination':'/wallet/'})
        else:
            braintree_error = result.message
    return render_to_response(tloc+'walletadd', dictcombine(
                    [maindict(request),
                     {'title':'Givology: Adding to Wallet',
                      'choice0'   : 'My Account',
                      'quantity'  : quantity,
                      'error'     : error,
                      'braintree_error' : braintree_error,
                      'braintree_client_side_encryption_key' : braintree_client_side_encryption_key,
                      'username'  : user.username,
                      'merchantid': gcheckout_id,
                      }]))


@reqDonor
def walletadded(request, user, profile, donor):
    '''
    for now this is just a test thing, so we can add money to peoples accounts.
    '''
    quantity = int(request.POST['quantity'])
    pw = Paymenttowallet(
        donor  = donor,
        amount = quantity,
        )
    pw.save()
    return render_to_response(tloc+'redirect', {
            'destination':'/wallet/'})

def accountrss(request):
    '''
    todo: need to somehow test to make sure that this is ... sane? can an rss aggregator even have a cookie?
    '''
    if not request.user.is_authenticated():
        return django.http.HttpResponseNotFound('rawr')
    user = apparent_user(request)
    profile = user.get_profile()
    obj = profile.get_object()
    f = feedgenerator.RssUserland091Feed(
        title=toutf(user.get_profile().name),
        description=toutf(user.get_profile().name+"'s updates."),
        link=u'http://www.givology.com/account/',
        )
    if isinstance(obj, Donor):
        recusers = [rec.profile.user for rec in obj.get_donatees()]
        for post in BlogPost.objects.filter(author__in=recusers).filter(iscomment=False).order_by('-created'):
            f.add_item(
                title=toutf(post.subject),
                description=toutf(post.subject),
                author_name=toutf(post.author.get_profile().name),
                link=u'http://www.givology.com/~%s/blog/%d/'%(post.author.username,post.id),
                pubdate=post.created,
                )
    if isinstance(obj, Organization):
        pass
    return django.http.HttpResponse(f.writeString('utf8'))

def donated(request):
    '''
    when someone tries donating
    '''
    #try:
    uname = None
    try: uname = request.POST['uname']
    except:
        return django.http.HttpResponse('Error: Must be accessed by form')
    try:
        grant = Grant.objects.get(id=int(request.POST['grantid']))
        rec = User.objects.get(username=uname).get_profile().get_object()
        don = apparent_user(request).get_profile().get_object()
        assert rec.profile.kind in ['s', 'p']
        assert don.profile.kind == 'd'
        assert grant.rec == rec
        amount = int(request.POST['donation'])
        if amount > don.have_informal():
            return django.http.HttpResponse('insufficient funds!')
        if amount < 1:
            return django.http.HttpResponse('can\'t just donate nothing!')
        pg = payGrant(don, grant, amount)
        if 'anon' in request.POST:
            set_attr('isanon', request.POST['anon'][0], pg)
        invalidatecache('impactthisweek')
        invalidatecache('nearlydone')
        return render_to_response(tloc+'thankyou.html', {'transaction_id':pg.id, 'fund_target':rec.profile.name,'fund_target_id':rec.profile.id,'fund_target_type':rec.profile.kind,'funder_id':don.id,'amount':amount,'url_referer':request.META['HTTP_REFERER']})
    except:
        return django.http.HttpResponseServerError(
            'Donation failure!?')

def blogrss(request, uname):
    try:
        user = User.objects.get(username=uname)
        vuser = apparent_user(request)
        assert canviewunapproved(request) or is_approved(user)
    except:
        return django.http.HttpResponseNotFound('username not found')
    f = feedgenerator.RssUserland091Feed(
        title=toutf(user.get_profile().name),
        description=toutf(user.get_profile().name+"'s updates."),
        author_name=toutf(user.get_profile().name),
        author_email=toutf(user.email),
        link=u'http://www.givology.com/~%s/blog'%(user.username),
        )
    for post in BlogPost.objects.filter(author=user).filter(iscomment=False).order_by('-created'):
        f.add_item(
            title=toutf(post.subject),
            description=toutf(post.subject),
            author_name=toutf(post.author.get_profile().name),
            link=u'http://www.givology.com/~%s/blog/%d/'%(post.author.username,post.id),
            pubdate=post.created,
            )
    return django.http.HttpResponse(f.writeString('utf8'))

def userblogview(request, uname, entry_id=None):
    try:
        user = User.objects.get(username=uname)
    except: return django.http.HttpResponseNotFound('username not found')

    name = User.objects.get(username=uname).get_profile().name

    choice1s = [{ 'uname': uname, 'name': name, }]

    return blogview(request, '/~'+uname+'/blog/',
                    "Givology: %s's blog" % (user.get_profile().name),
                    username=uname,
                    canwrite=apparent_user(request).username==uname,
                    #choice0=personalchoice(uname), choice1='Recent',
                    choice0='blogs', choice1s=choice1s,
                    entry_id=entry_id)

def notesfromthefield(request, entry_id=None):
    return blogview(request, '/notesfromthefield/', 'Givology: Notes from the Field', tagfilter='notes from the field', canwrite=apparent_user(request).is_staff, composeextra='&tags=notes from the field',choice0='Journal',choice1='Notes from the Field',entry_id=entry_id)

def news(request, entry_id=None):
    return blogview(request, '/news/', 'Givology: News', tagfilter='givology news', canwrite=apparent_user(request).is_staff, composeextra='&tags=givology news',choice0='Journal',choice1='News',entry_id=entry_id)

def studblogs(request, entry_id=None):
    return blogview(request, '/studentupdates/', 'Givology: Student Blog Posts', choice0='Journal', authorkind='s',entry_id=entry_id)

def projblogs(request, entry_id=None):
    return blogview(request, '/projectupdates/', 'Givology: Project Blog Posts', choice0='Journal', authorkind='p',entry_id=entry_id)




def blogpostfilter(request,username=None,tagfilter=None,authorkind=None):
    approved = not canviewunapproved(request)

    if 'tagfilter' in request.GET:
        tf2 = request.GET['tagfilter']
        tf2 = tf2.split(',')
        if tagfilter is None:
            tagfilter = tf2
        elif isinstance(tagfilter,str):
            tagfilter = [tagfilter]+tf2
        else:
            tagfilter += tf2

    posts = BlogPost.objects.order_by('-created')
    if username is not None:
        posts = posts.filter(
            author=User.objects.get(username=username))
    if approved:
        posts = posts.filter(approved = True)
    if isinstance(tagfilter,str):
        posts = posts.filter(tags__tag=tagfilter)
    elif tagfilter is not None and len(tagfilter) > 0:
        posts = posts.filter(tags__tag=tagfilter[0])
        if len(tagfilter) > 1:
            posts = [p for p in posts if p.hastags(tagfilter[1:])]
    if authorkind is not None:
        posts = [p for p in posts if p.author.get_profile().kind==authorkind]
    return posts





def blogview(request, baseurl, title,
             username=None, tagfilter=None, authorkind=None,
             canwrite=False, composeextra='',choice0='',choice1='', choice1s=[],
             entry_id=None):
    posts = blogpostfilter(request,username,tagfilter,authorkind)
    posts = posts.filter(iscomment=False)

    getstr = None #todo: figure out something for tags to add to filter

    titles = [p.titleinfo(baseurl=baseurl) for p in posts]

    md = None
    if username is not None:
        md = personaldict(request,username)
    else:
        md = maindict(request)
    md = dictcombine([md,{'title':title,
                          'titles':titles,
                          'choice0':choice0,
                          'choice1':choice1,
                          'choice1s':choice1s,
                          'canwrite':canwrite,
                          'composeextra':composeextra,
                          }])
    if entry_id is None:
        blog = paginate(request, posts, count0=5, width=5)
        blog['posts'] = [p.dicttorender(baseurl=baseurl)
                         for p in blog['objects']]
        blog['url'] = baseurl

        return render_to_response(tloc+'blogview', dictcombine(
            [md,
             {'blog': blog,
              'feedurl':'rss.xml',
              }]))
    else:
        cvu = canviewunapproved(request)
        vuser = apparent_user(request)
        post = None
        try:
            l = BlogPost.objects.filter(id=entry_id)
            if username is not None:
                l = l.filter(author=User.objects.get(username=username))
            if not (cvu or username == vuser.username):
                l = l.filter(approved=True)
            post = l[0]
        except:
            return django.http.HttpResponseNotFound('post not found')

        posts = post.children.all().order_by('-created')
        if not cvu:
            posts = posts.filter(approved=True)
        blog = paginate(request, posts, count0=10, width=5)
        blog['posts'] = [p.dicttorender() for p in blog['objects']]
        blog['url'] = baseurl
        dpost = post.dicttorender(baseurl=baseurl,getstr=getstr)


        try:
            m = IMsg(request=request, kind='comment', mode='compose', user=vuser)
        except:
            print gettraceback()
            return django.http.HttpResponseNotFound('Error parsing http GET. \n\nExample: http://www.givology.org/compose?type=message')

        commenting_enabled = True

        try:
            p = request.user.get_profile()
            need_captcha = not p.has_completed_captcha()
            captcha_html = False
            if need_captcha:
                captcha_html = captcha.new_captcha_html(None)
        except:
            captcha_html = False
            commenting_enabled = False

        return render_to_response(tloc+'blogpostview', dictcombine(
            [md,
             {'hascomments':len(blog['posts'])>0,
              'post': dpost,
              'blog': blog,
              'captcha_html': captcha_html,
              'commenting_enabled': commenting_enabled,
              'm': m,
              }]))

def deleteblogpost(request, post_id):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    try:
        bp = BlogPost.objects.get(id=int(post_id))
        u = apparent_user(request)
        assert u == bp.author
        if 'deleteit' in request.POST:
            bp.delete()
            return render_to_response(tloc+'redirect', {
                    'destination':'/~%s/blog/'%(u.username)})
        return render_to_response(tloc+'deleteblogpost', {
                'post':bp,
                })
    except:
        return render_to_response(tloc+'redirect', {
                'destination':'/'})

@specUser
def mailbox(request, uname, dir, user):
    tomax = 20

    if   dir=='in':
        if user == request.user:
            visit('inbox', user) #note that we have visited this page
        messages = Message.objects.filter(to=user)
    elif dir=='out':
        messages = Message.objects.filter(fr=user)
    if not canviewunapproved(request):
        messages = messages.filter(approved=True)

    sortby = 'sent'
    try:
        sortby = str(request.GET['sortby'])
        if sortby not in ['sent','subject']:
            sortby = 'sent'
    except: sortby = 'sent'
    if   sortby == 'sent':
        messages = messages.order_by('-created')
    elif sortby == 'subject':
        messages = messages.order_by('-created').order_by('subject')

    total_messages = messages.count()
    box = paginate(request, messages, count0=15, width=5)
    messages = [
        {'fr':message.fr.username,
         'from_img':message.fr.get_profile().get_image_url(width=50,height=50),
         'to':message.to,#temporary, will be overwritten
         'subject':message.subject,
         'created':message.created,
         'id':message.id} for message in box['objects']]
    for i in xrange(len(messages)):
        messages[i]['odd']=(i%2==1)
    for message in messages:
        tos = take(5, message['to'].all())
        to_img = None
        if len(tos)==1: to_img = tos[0].get_profile().get_image_url(width=50,height=50)
        tos = ''.join(take(tomax,', '.join([recvr.username for recvr in tos])))
        message['to'] = fif(len(tos)==tomax,tos+'...',tos)
        message['to_img']=to_img

    return render_to_response(tloc+'messages', dictcombine(
            [personaldict(request, uname),
             {'title':{'in':'In','out':'Out'}[dir]+'box: %s' %(user.get_profile().name),
              'messages':messages,
              'sortby':sortby,
              'blog' : box,
              'total':total_messages,
              'choice0':'dashboard',
              'choice1':{'in':'inbox','out':'outbox'}[dir],
              }]))

def inbox(request, uname):
    return mailbox(request, uname, 'in')
def outbox(request, uname):
    return mailbox(request, uname, 'out')



STYLE_CACHE_SECONDS = (10)

def givstyle(request):
    '''
    css file. using dictionary above to customize things, and make
    things inherit the same across classes... unfortunately ie doesnt
    seem to like the "inherit".
    '''
    resp = render_to_response(tloc+'givstyle.css',style_dict)
    resp['Cache-Control'] = 'max-age=%i' % (STYLE_CACHE_SECONDS)
    return resp

def newpassword(request):
    '''
    '''
    if 'newpwinfo' in request.REQUEST:
        dcode = None
        try:
            dcode = urlsafe_b64decode(
                request.REQUEST['newpwinfo'])
        except:
            return django.http.HttpResponse('Invalid confirmation link.')
        msg = dcode[:-16]
        print msg
        mac = hmac.new(hmac_key, msg).digest()
        if mac != dcode[-16:]:
            return django.http.HttpResponse('Invalid confirmation link.')
        if 'newpwinfo' in request.POST:
            dict = pickle.loads(msg)
            try:
                u = User.objects.get(id=dict['uid'])
                u.password = dict['pw']
                u.save()
            except:
                return django.http.HttpResponse(
                    'Error in parsing confirmation data.')
            return render_to_response(tloc+'redirect', {'destination':'/login/','mesg':'Password changed! Try it out!'})
        else:
            return render_to_response(
                tloc+'newpasswordemailpost',
                {'newpwinfo':request.REQUEST['newpwinfo']})
    if   ('resetmethod' in request.POST and
          request.POST['resetmethod'] == 'withemail'):
        if User.objects.filter(username=request.POST['username']).count() < 1:
            return django.http.HttpResponse('That username is not in the system.')
        dict = {'uid' : int(User.objects.get(
                    username=request.POST['username']).id),
                'pw' : hashpassword(request.POST['newpassword']),
                'email' : str(User.objects.get(
                    username=request.POST['username']).email)}
        msg = pickle.dumps(dict)
        mac = hmac.new(hmac_key, msg).digest()
        code = urlsafe_b64encode(msg + mac)
        link = 'https://www.givology.org/newpassword/?newpwinfo=%s' % code

        fr = 'Givology <no-reply@givology.org>'
        to = dict['email']
        subject = 'Givology Password Change'
        body = "Complete your Givology password change by following this link:\r\n\r\n%s\r\n\r\n Givology" % (link)
        sendmail(fr, to, subject, body)
        return render_to_response(tloc+'newpasswordemail', dictcombine(
                [maindict(request),
                 {'title':'Givology',
                  'choice0': 'About',
                  }]))
    if ('resetmethod' in request.POST and
        request.POST['resetmethod'] == 'withpassword'):
        user = authenticate(
            username=request.POST['username'],
            password=request.POST['oldpassword'])
        if user is None:
            return django.http.HttpResponse('Either that username is not in the system or the old password did not match.')
        user.set_password(request.POST['newpassword'])
        user.save()
        return render_to_response(tloc+'redirect',
                                  {'destination':'/login/',
                                   'mesg':'Password changed! Try it out!'})
    return render_to_response(tloc+'newpassword', dictcombine(
            [maindict(request),
             {'title':'Givology',
              'choice0': 'About',
              }]))


def login_view(request):
    '''
    the login view. needs to be prettied up on the template/css side
    of things.
    '''
    if request.method == 'POST':
        if 'fauxuid' in request.POST:
            if sudoid(request, sureint(request.POST['fauxuid'])):
                return render_to_response(
                    tloc+'redirect',
                    {'destination':'/account/'})
            else:
                return django.http.HttpResponseNotFound('rawr! failed sudo!')
        try:
            username = request.POST['username']
            password = request.POST['password']
        except:
            username = ''
            password = ''
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            #return HttpResponseRedirect('/')
            return render_to_response(
                tloc+'redirect',{'destination':'/account/'})
        else:
            return render_to_response(
                tloc+'login',
                {'title':'Givology: Login','login_fail':True})
    else:
        return render_to_response(
            tloc+'login',
            {'title':'Givology: Login','login_fail':False})

def logout_view(request):
    '''
    where to go when you choose 'logout'. this just gives a
    redirection page to the main page at the moment.
    '''
    if request.POST['logaction']=='logout' and request.user.is_authenticated():
        if 'fauxuid' in request.session:
            ''' just brings you back to yourself :) '''
            sudone(request)
            return render_to_response(tloc+'redirect',{'destination':'/account/'})
        else:
            logout(request)
    return render_to_response(tloc+'redirect',{'destination':'/'})



def sponsorships(request):
    return render_to_response(tloc+'sponsorships', dictcombine(
            [maindict(request),
             {'choice0':'Give',
              }]))
def merchandise(request):
    return render_to_response(tloc+'merchandise', dictcombine(
            [maindict(request),
             {'choice0':'Give',
              }]))
def getinvolveddonate(request):
    return render_to_response(tloc+'getinvolveddonate', dictcombine(
            [maindict(request),
             {'choice0':'Get Involved',
              }]))


def policy(request):
    return render_to_response(tloc+'policy', dictcombine(
            [maindict(request),
             {'choice0':'About',
              }]))

def terms(request):
    return render_to_response(tloc+'terms', dictcombine(
            [maindict(request),
             {'choice0':'About',
              }]))

def messagesearch(request):
    '''
    admin-only

    searches messages.

    (todo)
    '''
    user = apparent_user(request)
    if not user.is_staff:
        return django.http.HttpResponse('staff only, sorry!')

    frkind = None
    try:
        frkind = request.GET['frkind']
        assert frkind in ['s','p','d','o']
    except:
        frkind = None
    tokind = None
    try:
        tokind = request.GET['tokind']
        assert tokind in ['s','p','d','o']
    except:
        tokind = None
    frorg = None
    toorg = None




    return

def donorstats(request):
    from datetime import date

    user = apparent_user(request)
    if not user.is_staff:
        return django.http.HttpResponse('staff only, sorry!')
    ds = Donor.objects.all()
    es = [d.profile.user.email for d in ds]
    es = [e for e in es if isemailvalid(e)]
    es = ', '.join(es)

    t = min(Paymenttowallet.objects.all(
            ).order_by('created')[0].created,
            Paymenttogrant.objects.all(
            ).order_by('created')[0].created
            )
    t -= datetime.timedelta(days = date.weekday(t),
                            hours = t.hour,
                            minutes = t.minute,
                            seconds = t.second)

    week = datetime.timedelta(days=7)
    now = datetime.datetime.now()

    weekbreakdowns = []
    while t < now:
        pws = Paymenttowallet.objects.filter(
            created__gt=t).filter(
            created__lt=t + week)
        pwa = sum([p.amount for p in pws])
        pws = pws.count()
        pgs = Paymenttogrant.objects.filter(
            created__gt=t).filter(
            created__lt=t + week)
        pga = sum([p.amount for p in pgs])
        pgs = pgs.count()
        weekbreakdowns += [{
                't':t,
                'weekstart':t.strftime('%Y-%m-%d'),
                'pwa':pwa,
                'pga':pga,
                'pws':pws,
                'pgs':pgs,
                }]

        t += week

    return render_to_response(tloc+'donorstats', dictcombine(
            [maindict(request),
             {'choice0':'Community',
              'emails':es,
              'weekbreakdowns':weekbreakdowns,
              'countpw':Paymenttowallet.objects.all().count(),
              'totalpw':sum(p.amount for p
                            in Paymenttowallet.objects.all()),
              'countpg':Paymenttogrant.objects.all().count(),
              'totalpg':sum(p.amount for p
                            in Paymenttogrant.objects.all()),
              }]))

@adminOnly
def donorcsv(request,user):
    sl = ['username,email,join date,pledged,donated,giftcerts out,giftcerts in,balance']
    return django.http.HttpResponse('\r\n'.join(
        sl+
        [','.join([csvencode(str(a)) for a in [
            d.profile.user.username,
            d.profile.user.email,
            d.profile.user.date_joined.strftime('%D'),
            d.pledged_informal(),
            d.donated_informal(),
            d.gift_cert_out(),
            d.gift_cert_in(),
            d.pledged_informal()+d.gift_cert_balance()-d.donated_informal(),
            ]
                   ]) for d in Donor.objects.all().order_by('id')]
        ), mimetype="text/plain")


@adminOnly
def recipcsv(request,user):
    sl = 'username,name,is approved,kind,country,grant count,grant amount,grant balance,partner username,partner name,partner country'
    csvl = [sl]
    for r in Recipient.objects.all().order_by('id'):
        p = r.profile
        gc = 0
        ga = 0
        gb = 0
        rop = r.org.profile
        for g in r.grant_set.all():
            g.update()
            gc += 1
            ga += g.want
            gb += g.have_very_informal
        l = [p.user.username,
             p.name,
             r.approved,
             {'p':'Project','s':'Student'}[p.kind],
             get_attr('country',p,'no country information'),
             gc, ga, gb,
             rop.user.username,
             rop.name,
             get_attr('country',rop,'no country information')]
        csvl.append(','.join([csvencode(str(a)) for a in l]))
    #print csvl
    return django.http.HttpResponse('\r\n'.join(csvl), mimetype="text/plain")


def partnersum(partner, start=None, end=None):
    if end is None:
        end = datetime.datetime.now()
    if start is None:
        start = datetime.datetime(year=1980,month=1,day=1)
    return fromNone(
        0,runquery(mkquery('sum(pg.amount)',
                           ['giv_paymenttogrant pg',
                            'giv_recipient r',
                            'giv_grant g',
                            'giv_organization o'],
                           ['o.id=?',
                            'r.org_id=o.id',
                            'g.rec_id=r.id',
                            'pg.grant_id=g.id',
                            'pg.created >= ?',
                            'pg.created < ?',
                            ]),
                   [str(partner.id),
                    start,
                    end,
                    ])
        )
def partnersum_c(partner, start=None, end=None):
    if end is None:
        end = datetime.datetime.now()
    if start is None:
        start = datetime.datetime(year=1980,month=1,day=1)
    return sum(
        [Grant.objects.get(id=gid).want for gid
         in runquery(mkquery('distinct g.id',
                             ['giv_paymenttogrant pg',
                              'giv_recipient r',
                              'giv_grant g',
                              'giv_organization o'],
                             ['o.id=?',
                              'r.org_id=o.id',
                              'g.rec_id=r.id',
                               'g.left_very_informal=0',
                              'pg.grant_id=g.id',
                              'pg.created >= ?',
                              'pg.created < ?',
                              ]),
                     [str(partner.id),
                      start,
                      end,
                      ], r = None)
         if Grant.objects.get(id=gid).want <= fromNone(
             0,runquery(mkquery('sum(pg.amount)',
                                ['giv_paymenttogrant pg'],
                                ['pg.grant_id = ?',
                                 'pg.created < ?',
                                 ]),
                        [str(gid),
                         end]))
         ])


@adminOnly
def partnerstats(request,user):

    first = Paymenttogrant.objects.all().order_by('created')[0]
    q0 = getquarter(first.created)
    ql = takewhile(
        (lambda x : x <= getquarter(datetime.datetime.now())),
        iteratef(quarternext, q0))

    partners = [{
        'uname':p.profile.user.username,
        'name':p.profile.name,
        'want':sum([g.want for g in xconcat(
            [r.grant_set.all() for r in
             Recipient.objects.filter(org=p)
             if r.approved
             ])]),
        'total':partnersum(p),
        'completed':partnersum_c(p),
        'studs':Recipient.objects.filter(
            profile__kind='s').filter(org=p).filter(approved=True).count(),
        'projs':Recipient.objects.filter(
            profile__kind='p').filter(org=p).filter(approved=True).count(),
        'completestuds':len([
            1 for r in Recipient.objects.filter(
                profile__kind='s').filter(org=p)
            if r.curgrant().iscomplete()]),
        'completeprojs':len([
            1 for r in Recipient.objects.filter(
                profile__kind='p').filter(org=p)
            if r.curgrant().iscomplete()]),
        'quarters':
        [{'in': partnersum(
            p, quarterstart(q), quarterstart(quarternext(q))),
          'til': partnersum(
            p, end = quarterstart(quarternext(q))),
          'c_in': partnersum_c(
            p, quarterstart(q), quarterstart(quarternext(q))),
          'c_til':partnersum_c(
            p, end = quarterstart(quarternext(q))),
          }
         for q in ql],
        }
        for p in Organization.objects.all()]


    return render_to_response(tloc+'partnerstats', dictcombine(
            [maindict(request),
             {'choice0':'Community',
              'partners':partners,
              'quarters':[str(quarterstart(q).date()) + ' to ' +
                          str(quarterend(q).date())
                          for q in ql]
              }]))


def recipientsum(rec, start=None, end=None):
    if end is None:
        end = datetime.datetime.now()
    if start is None:
        start = datetime.datetime(year=1980,month=1,day=1)
    return fromNone(
        0,runquery(mkquery('sum(pg.amount)',
                           ['giv_paymenttogrant pg',
                            'giv_recipient r',
                            'giv_grant g'],
                           ['r.id=?',
                            'g.rec_id=r.id',
                            'pg.grant_id=g.id',
                            'pg.created >= ?',
                            'pg.created < ?',
                            ]),
                   [str(rec.id),
                    start,
                    end,
                    ])
        )
def recipientstats(request):
    user = apparent_user(request)
    if not user.is_staff:
        return django.http.HttpResponse('staff only, sorry!')

    first = Paymenttogrant.objects.all().order_by('created')[0]
    q0 = getquarter(first.created)
    ql = takewhile(
        (lambda x : x <= getquarter(datetime.datetime.now())),
        iteratef(quarternext, q0))

    recipients = [
        {'name':r.profile.name,
         'have':r.curgrant().have_informal(),
         'want':r.curgrant().want,
         'partner':r.org.profile.name,
         'kind':fif(r.profile.kind=='s','student','project'),
         'userid':r.profile.user.id,
         'completed':r.curgrant().iscomplete(),
         'quarters':
         [{'in': recipientsum(
             r, quarterstart(q),
             quarterstart(quarternext(q))),
           'til': recipientsum(
               r, end = quarterstart(quarternext(q))),
           }
          for q in ql],
         }
        for r in Recipient.objects.all()]


    return render_to_response(tloc+'recipientstats', dictcombine(
            [maindict(request),
             {'choice0':'Community',
              'recipients':recipients,
              'quarters':[str(quarterstart(q).date()) + ' to ' +
                          str(quarterend(q).date())
                          for q in ql]
              }]))




def giftcertificates(request):
    #if not request.user.is_authenticated():
    #    return render_to_response(tloc+'redirect', {
    #            'destination':'/login/'})
    user = None
    profile = None
    donor = None
    try:
        user = apparent_user(request)
        profile = user.get_profile()
        donor = profile.get_object()
        if profile.kind != 'd':
            return django.http.HttpResponse(
                'Only Donors can access this')
    except: pass

    rdict = request.POST
    gc = None
    amount = None
    action = None
    try: action = request.POST['action']
    except: pass

    if action == 'create' and donor is not None:
        try: amount = int(request.POST['amount'])
        except:
            return django.http.HttpResponse(
                'Error in gift certificate creation')
        if amount > donor.have_informal():
            return django.http.HttpResponse(
                'Insufficient funds in wallet for a ' +
                'gift certificate of $%i.' % (amount))
        while True:
            r = randint56()
            if GiftCert.objects.filter(key=r).count()==0: break
        gc = GiftCert(creator=donor,
                      key=str(r),
                      amount=amount)
        gc.save()

        name = ''
        try: name = tagclean(rdict['name'])
        except: pass
        bmesg = ''
        try: bmesg = tagclean(rdict['bmesg'])
        except: pass
        emails = [user.email]
        if 'email' in rdict and len(rdict['email']) > 3:
            if isemailvalid(rdict['email']):
                emails.append(rdict['email'])
            else:
                django.http.HttpResponse(
                    'Email appears invalid...')
        gcnum = 0
        try: gcnum = str(int(rdict['gcnum']))
        except: pass

        gcdict = {'name':name,
                  'bmesg':bmesg,
                  'from':profile.name,
                  'fromu':user.username,
                  'code':str(r),
                  'amount':amount,
                  }
        tmpl = 'giftcerts/giftcert'+gcnum+'body.html'
        htmlbody = ('<html><head></head><body>' +
                    render_to_response(tmpl, gcdict).content +
                    '</body></html>')
        if islive:
            for a in emails:
                sendmail('giv_updates@givology.org',
                         a,
                         'Gift Certificate for Givology',
                         'Greetings, '+name+', you have received a gift certificate of $'+str(amount)+' for Givology!\n\nLog in to Givology and visit https://www.givology.org/giftcert/ to use the code '+str(r)+' and accept it!',
                         htmlbody = htmlbody)
        else: print 'Greetings, '+name+' you have received a gift certificate of $'+str(amount)+' for Givology!\n\nLog in to Givology and visit https://www.givology.org/giftcert/ to use the code '+str(r)+' and accept it!'

        return render_to_response(
            tloc+'giftcertty.html', dictcombine(
                [maindict(request),
                 {'choice0':'Give',
                  'tinymce':False,
                  'tmpl':tmpl,
                  },
                 gcdict,
                 ]))
            #django.http.HttpResponse(
            #'Gift certificate created with key %s; ' % (str(r))+
            #'check your email to see it.')
    elif action == 'use' and donor is not None:
        try: gc = GiftCert.objects.get(key=rdict['key'])
        except: return django.http.HttpResponse(
            'No gift certificate with that key '+
            'in the system.')
        if gc.receiver is not None:
            return django.http.HttpResponse(
                'This gift certificate has been accepted by '+
                'user %s'%(gc.receiver.profile.user.username))
        gc.receiver = donor
        gc.save()
        return django.http.HttpResponse(
            'Received gift certificate for $%i.'%(gc.amount))
    warnuser = donor is None
    warnwallet = False
    if donor is not None:
        warnwallet = donor.have_informal() < 1
    return render_to_response(tloc+'gift-certificates.html', dictcombine(
            [maindict(request),
             {'title':'Givology: Gift Certificates',
              'choice0':'giv-now',
              'choice1' : 'gift-certificates',
              'warn' : (warnuser or warnwallet),
              'warnuser' : warnuser,
              'warnwallet' : warnwallet,
              }]))

@reqDonor
def accept_gift_card(request, user, profile, donor):
    try: gc = GiftCert.objects.get(key=request.POST['confirmation-key'])
    except: return django.http.HttpResponse(
        'No gift certificate with that key '+
        'in the system.')
    if gc.receiver is not None:
        return django.http.HttpResponse(
            'This gift certificate has already been accepted by ' +
            'user %s'%(gc.receiver.profile.user.username))
    gc.receiver = donor
    gc.save()
    return django.http.HttpResponse(
        'Received gift certificate for $%i.'%(gc.amount))

def comm_about(request):
    return render_to_response(tloc+'community', dictcombine(
            [maindict(request),
             {'choice0':'Community',
              }]))

def getinv_about(request):
    return render_to_response(tloc+'getinvabout', dictcombine(
            [maindict(request),
             {'choice0':'Get Involved',
              }]))

def errorpage(request):
    assert False

def servererror(request):
    import traceback

    print 'server error!'
    e, f, t = sys.exc_info()
    ts = traceback.format_exc(t)

    #sendmail(fr='giv_updates@givology.org',
    #         to='carljmackey@gmail.com',
    #         subject='Givology Error',
    #         body=ts+'\n\n\n'+str(request))
    return render_to_response(tloc+'500.html',{})


def markfellow(request):
    if not request.user.is_staff:
        return django.http.HttpResponse('no entry!')

    uname = None

    if 'uname' in request.POST:
        uname = request.POST['uname']
        set_attr('isfellow', 'True',
                 User.objects.get(username=uname))

    return render_to_response(tloc+'markfellow', dictcombine(
            [{'uname':uname,
              }]))


def robotstxt(request):
    return django.http.HttpResponse('')
def faviconredir(request):
    return django.http.HttpResponseRedirect('/images/givicon.ico')

def nyc(request):
    return render_to_response(tloc+'nyc.html', dictcombine(
        [maindict(request),
         {'choice0':'Community'}]))


@adminOnly
def donationcsv(request, user):
    r = '\r\n'.join((','.join([
        csvencode(str(a)) for a in [
            pg.donor.profile.user.username,
            pg.donor.profile.name,
            pg.donor.profile.user.email,
            pg.grant.rec.profile.user.username,
            fif(pg.grant.rec.profile.kind=='s',
                'Student','Project'),
            pg.grant.rec.org.profile.user.username,
            pg.grant.id,
            pg.amount,
            pg.grant.want,
            sumpg(grant=pg.grant,createdbefore=pg.created),
            pg.amount+sumpg(grant=pg.grant,
                            createdbefore=pg.created),
            pg.isanon(),
            pg.created.strftime('%D'),
            ]
        ]) for pg in Paymenttogrant.objects.all(
                       ).order_by('created')))
    return django.http.HttpResponse(
        'donor username,donor name,donor email address,recipient username,recipient kind,partner username,grant id,payment amount,grant amount,total pre-donation,total post-donation,anonymous,donation date\r\n'+r, mimetype="text/plain")

@adminOnly
def paymentcsv(request, user):
    r = '\r\n'.join((','.join([
        csvencode(str(a)) for a in [
            pw.donor.profile.user.username,
            pw.donor.profile.name,
            pw.donor.profile.user.email,
            pw.kind,
            pw.amount,
            pw.created.strftime('%D'),
            ]
        ]) for pw in Paymenttowallet.objects.all(
                       ).order_by('created')))
    return django.http.HttpResponse(
        'donor username,donor name,donor email address,kind,amount,payment date\r\n'+r, mimetype="text/plain")

@adminOnly
def giftcertcsv(request, user):
    def recvd(a):
        try: return gc.received.strftime('%D')
        except: return ''
    def getreceiver(gc):
        try: return gc.receiver.profile.user.username
        except: return ''
    r = '\r\n'.join((','.join([
        csvencode(str(a)) for a in [
            gc.creator.profile.user.username,
            getreceiver(gc),
            gc.key,
            gc.amount,
            gc.created.strftime('%D'),
            recvd(gc)
            ]
        ]) for gc in GiftCert.objects.all(
                       ).order_by('created')))
    return django.http.HttpResponse(
        'username from,username to,key,amount,creation date,recept date\r\n'+r, mimetype="text/plain")


@adminOnly
def addgrant(request, uname, user):
    if request.method == 'POST':
        g = Grant(rec=User.objects.get(username=uname).get_profile().get_object(), want=10)
        g.save()
        g.update()
        return render_to_response(
            tloc+'redirect',
            {'destination':'/~'+uname+'/editprofile/',
             'mesg':'Now, edit the grant portion of the profile'
             })
    else:
        return django.http.HttpResponse('''
<http>
<head></head>
<body>
<form action="." method="POST">
Create a new grant for '''+uname+'''? Note that you will then have to edit it in the editprofile page. <br />
<input type="submit" value="Ok" />
</form>
</body>
</http>
''')


@adminOnly
def adddonor(request, user):
    '''
    ugly copy-pasted donor adding thing for admins to do
    '''
    form = uform.newdonorform(request)
    v = False
    u = None
    p = None
    d = None
    if request.method == 'POST':
        form.apply(request.POST)
        v = form.verify()
    if v:
        dict=form.retrieve()
        if not is_valid_username(dict['username']):
            return django.http.HttpResponse(
                'Usernames must be only letters and numbers')
        if User.objects.filter(
            username=dict['username']).count() != 0:
            return django.http.HttpResponse(
                dict['username'] + ' already exists')
        if not isemailvalid(dict['email']):
            return django.http.HttpResponse(
                'email address looks invalid...')

        #hash password now, so that it's never sent raw.
        dict['password'] = hashpassword(dict['password'])

        if (User.objects.filter(
            username=dict['username']).count() != 0):
            logvisit('confirmnewdonor - already', request)
            return render_to_response(
                tloc+'redirect',
                {'destination':'/login/',
                 'mesg':'Account already confirmed. Sending you to login!'
                 })
        u = User.objects.create_user(
            username=dict['username'],
            email=dict['email'],
            password=dict['password'])
        #to make sure that it doesn't run the hash again...
        u.password=dict['password']
        u.save()
        p = UserProfile(user=u,
                        name=dict['name'],
                        kind='d')
        p.save()
        set_attr('isanon','f',p)
        d = Donor(profile=p)
        d.save()
        invalidatecache('impactthisweek')

        form = uform.newdonorform(request)

    return render_to_response(tloc+'adddonor',dictcombine(
        [maindict(request),
         {'title':'Givology: Add Donor',
          'choice0':'Community',
          'form':form.renderhtml(),
          'p':p,
          }]))



# HACK4IMPACT VIEWS

@reqUser
@csrf_exempt
def saveVolunteerHours(request, user, profile, obj):
    message = "failed"
    if request.is_ajax():
        try:
            when = datetime.datetime.now()
            vw = VolunteerWork(
                volunteer=user,
                minutes=int(request.POST["volunteer_hours"]),
                action=request.POST["volunteer_activity"],
                when=when
           )
            vw.save()
            message = "success"
        except:
            print 'error in volunteered'
            pass
    return django.http.HttpResponse(message)


@reqUser
def dashboard(request, user, profile, obj):
    # d = searchrecipients(request, 's')

    profile = user.get_profile()
    obj = profile.get_object()

    pgs = list(Paymenttogrant.objects.filter(
        donor=obj).order_by('-created'))

    recs =[Recipient.objects.get(id=i)
           for i in xremoveduplicates(
            pg.grant.rec.id for pg
            in pgs)
           ]


    print time.clock()


    total = 0;
    recs2=[];
    for rec in recs:
        rec2 = rec.profile.summary();
        rec2['large_img']= rec.profile.get_image_url(206, 206);
        recs2.append(rec2);


    recs = recs2;
    for rec in recs:
        rec['messageme']=True
        rec['my_given'] = sum(
            [pg.amount for pg in pgs if pg.grant.rec.id == rec['obj_id']])
        total += rec['my_given'];
        rec['my_given_percent'] = int((100.0*rec['my_given']) / rec['grant_have_total'])
        print rec['large_img'];
        print (" -------------------");


    # trending
    ret = []
    seen = set()
    grant_count = Paymenttogrant.objects.count()
    for i in range(0, grant_count, 10):
        if len(ret) >= 10:
            break
        recent_payments = list(Paymenttogrant.objects.order_by('-created')[i:i+10])
        if len(recent_payments) == 0:
            break
        for payment in recent_payments:
            if payment.grant.rec.profile.url() in seen:
                continue
            seen.add(payment.grant.rec.profile.url())
            temp = {
                'img':payment.grant.rec.profile.get_image_url(206, 206),
                'url':payment.grant.rec.profile.url()
                }
            ret.append(temp)
            print len(ret)


    # similar

    possible_curr = list(Donor.objects.filter(profile=profile))
    if (len(possible_curr) == 1):
        recs2 = possible_curr[0].get_donatees()
    else:
        recs2 = []

    other_donors = []
    # maybe break this out early if it gets to 5
    for rec in recs2:
        for donor in rec.get_donors():
            other_donors.append(donor)

    donatees = set()
    for other_donor in other_donors:
        for donatee in other_donor.get_donatees(): 
            donatees.add(donatee)

    donatees_exclude = [donatee for donatee in donatees if donatee not in recs2]
    random_sample = random.sample(donatees_exclude, (20 if 20 < len(donatees_exclude) else len(donatees_exclude)))

    ret2 = []
    for org in random_sample:
        temp = {
            'img':org.profile.get_image_url(206, 206),
            'url':org.profile.url()
            }
        ret2.append(temp)


    # blog

    volunteer_works = list(VolunteerWork.objects.filter(volunteer=user).order_by('-when'))

    return render_to_response(tloc+'dashboard.html', dictcombine(
        [maindict(request), 
        {'results': recs,
        'data': ret,
        'data2': ret2,
        'volunteer_works' : volunteer_works,
        'total': total}]))


