
from   base64 import urlsafe_b64encode, urlsafe_b64decode
import copy
import datetime
import sha
import hmac
import math
import os
import pickle
import random
import re
import stat
from   string import lower, count
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


from   proj.giv.consts import *

from   proj.giv.htmlconv import tagclean, tagunclean, forshow
from   proj.giv.utils import *
from   proj.giv.db import *
from   proj.settings import *

import proj.giv.uform as uform
from   proj.giv.models import *
from   proj.giv.cache import *


'''
donorbot stuff
'''
def donorbot_user():
    try:
        u = User.objects.get(username='donorbot')
    except:
        u = User.objects.create_user(username='donorbot',
                                     email='nobody@nowhere.com',
                                     password='ifwqejr9cfmi4mjcfije0')
        u.save()
        u = User.objects.get(username='donorbot')
    return u
def donorbot_profile():
    u = donorbot_user()
    try:
        p = u.get_profile()
    except:
        p = UserProfile(user=u,
                        name='donorbot',
                        kind='d')
        p.save()
        p = u.get_profile()
    return p
def donorbot_donor():
    p = donorbot_profile()
    try:
        d = p.get_object()
    except:
        d = Donor(profile=p)
        d.save()
        d = p.get_object()
    return d


'''
navbar stuff
'''

def slashredir(request, url0, url1):
    return django.http.HttpResponseRedirect('/%s%s/'%(url0,url1))


class Nav: 
    def __init__(self, label, href, subnavbar=[], n=0):
        self.label = label
        self.href = href
        self.subnavbar = subnavbar
        self.n = n
        for i in xrange(len(self.subnavbar)):
            self.subnavbar[i].n=i
    

# Main
_us = Nav('How Givology Works', '/about/')
_vision = Nav('Vision and Mission', '/vision/')
_team = Nav('Our Team', '/team/')
_FAQ = Nav('FAQ', '/FAQ/')
_contact = Nav('Contact Us', '/contact/') 
_becomeapartner = Nav('Become a Partner', '/partnerships/')
_main = Nav(
    'About', '/about/',
    [_us, _vision, _team, _FAQ, _contact, _becomeapartner],
    n=0)
# Donate / Give
_students = Nav('Students', '/donate/students/')
_projects = Nav('Projects', '/donate/projects/')
_ffstudents = Nav('Fully Funded Students', '/donate/ffstudents/')
_ffprojects = Nav('Fully Funded Projects', '/donate/ffprojects/')
_giftcerts = Nav('Gift Certificates', '/giftcert/')
_sponsorships = Nav('Support Us', '/sponsorships/')
_merchandise = Nav('Merchandise', '/merchandise/')
_donate = Nav(
    'Give', '/donate/',
    [_students, _projects, 
     _sponsorships, _giftcerts, _merchandise],
    n=1)
# Community
_donors = Nav('Our Donors', '/donors/')
_fpartners = Nav('Our Field Partners','/partners/')
_teamstmp = Nav('Giving Teams', '/comingsoon/')
_teams = Nav('Giving Teams', '/teams/')
_multimedia = Nav('Multimedia', '/multimedia/')
_community = Nav(
    'Community', '/community_about/',
    [_donors, _fpartners, _teams, _multimedia],
    n=2)
# Journal
_news = Nav('News', '/news/')
_studblogs = Nav('Student Updates', '/studentupdates/')
_projblogs = Nav('Project Updates', '/projectupdates/')
_notesfrom = Nav('Notes from the Field', '/notesfromthefield/')
_journal = Nav(
    'Journal', '/news/',
    [_news, _studblogs, _projblogs, _notesfrom],
    n=5)
# Get Involved
_startachapter = Nav('Start a Chapter', '/startachapter/')
_volunteer = Nav('Volunteer', '/volunteer/')
_internships = Nav('Internships', '/internships/')
_fellowships = Nav('Fellowships', '/fellowships/')
_spreadtheword = Nav('Spread the Word', '/spreadtheword/')
_partnerships = Nav('Apply to be a Partner', '/partnerships/')

_gdonate = Nav('Donate', '/gdonate/')
_getinvolved = Nav(
    'Get Involved', '/getinvolved_about/',
    [_startachapter, 
     _volunteer,
     _internships,
     _fellowships,
     _spreadtheword],
    n=3)
# Top Navigation Bar
_navbar = [_main, _community, _donate, _journal,  _getinvolved]

def anavbar(user):
    if user.is_authenticated():
        # Account
        _portfolio = Nav('Dashboard', '/account/')
        _wallet = Nav('My Wallet', '/account/#wallet')
        _profile = Nav('My Profile', '/~%s/'%(user.username)) #
        _blog = Nav('My Blog', '/~%s/blog/'%(user.username))  # consider just making these links of some kind in the body...
        _inbox = Nav('Inbox', '/~%s/inbox/'%(user.username))
        _outbox = Nav('Outbox', '/~%s/outbox/'%(user.username))
        _account = Nav('My Account', '/account/',
                       [_portfolio, _profile,
                        _blog, _inbox, _outbox], n=4)
        return _navbar+[_account]
    else:
        return _navbar

def navbar(user):
    n = copy.deepcopy(anavbar(user))
    for sn in n:
        sn.subnavbar.reverse()
    n.reverse()
    return n

def personalchoice(uname):
    user = User.objects.get(username=uname)
    if user.get_profile().kind in ['s','p']:
        return 'Give'
    else:
        return 'Community'

#personal stuff
def personalbar(uname, user, kind):
    return navbar(user)
    
    #temporarily removing this until i can think of something better...?
    
    # Users
    _pubview = Nav('%s: Profile'%(uname), '/~%s/'%(uname))
    _blog = Nav('%s: Blog'%(uname), '/~%s/blog/'%(uname))
    _ncommunity = copy.deepcopy(_community)
    _ncommunity.subnavbar+=[_pubview,_blog]
    _ndonate = copy.deepcopy(_donate)
    _ndonate.subnavbar+=[_pubview,_blog]
    nlist = copy.copy(anavbar(user))
    if kind in ['s','p']:
        nlist.remove(_donate)
        nlist.insert(2,_ndonate)
    else:
        nlist.remove(_community)
        nlist.insert(1,_ncommunity)
    return nlist







def maindict(request, user=None):
    if user is None:
        user = apparent_user(request)
    dict = {'user':user,
            'updatecounts':updatecounts(user),
            'navbar': navbar(user),
            'isloggedin': request.user.is_authenticated(),
            'isstaff':False,
            'isfellow':False,
            'islive':islive,
            'https':request.is_secure(),
            'http':not request.is_secure(),
            'constant':constants(),
            }
    if user.is_authenticated():
        profile = user.get_profile()
        obj = profile.get_object()
        if isinstance(obj, Donor):
            dict.update({'balance':formnum(profile.get_object().have_informal()),'clientisdonor':True})
        if profile.isanon():
            dict['vieweranon']=True
        dict['isstaff'] = user.is_staff
        dict['isfellow'] = get_attr('isfellow',user,'False')
    return dict

def personaldict(request, uname, user=None):
    if user is None:
        user = apparent_user(request)
    huser = User.objects.get(username=uname)
    dict = maindict(request, user)
    dict.update({
            'navbar':personalbar(uname, user, huser.get_profile().kind),
            'uname' :uname,
            })
    return dict


def is_approved(thing):
    if isinstance(thing, User):
        obj = thing.get_profile().get_object()
        return (not isinstance(obj,Recipient)) or (obj.approved)
    elif isinstance(thing, BlogPost):
        user = thing.author
        obj = user.get_profile().get_object()
        return (not isinstance(obj,Recipient)) or (not obj.postneedapproval)
    return False


def province_f(d):
    country = d['country']
    kind = d['kind']
    
    froms = ['giv_attrib a',
             'giv_attrval av',
             'giv_userprofile p']
    wheres = ['a.id = av.attr_id',
              'a.name = "province"',
              'av.oid = p.id',
              ]
    values = []
    if kind in ['s','student']:
        wheres += ['p.kind = "s"']
    if kind in ['d','donor']:
        wheres += ['p.kind = "d"']
    if kind in ['p','project']:
        wheres += ['p.kind = "p"']
    if country is not None:
        froms += ['giv_attrib a1','giv_attrval av1']
        wheres += ['a1.id = av1.attr_id',
                   'a1.name = "country"',
                   'av1.oid = av.oid',
                   'av1.val = ?']
        values += [country]
    query = mkquery('distinct av.val',
                    froms, wheres, 'av.val')
    cursor = connection.cursor()
    cursor.execute(query, values)
    provinces = []
    while True:
        try:
            provinces.append(str(cursor.fetchone()[0]))
        except: break
    return provinces

def get_provinces(country=None, kind=None):
    cachename = 'provinces'+fif(
        country is not None,
        '_country_%s'%(country), '')+fif(
        kind is not None,
        '_kind_%s'%(kind),'')
    provinces = withcache(cachename,
                          province_f,
                          {'country':country,
                           'kind':kind},
                          duration=1*60)
    return provinces

def get_countries(kind = None):
    cachename = 'countries'+fif(
        kind is not None,'_kind_%s'%kind,'')
    countries = cache.get(cachename, None)
    if countries is None:
        query = (
            'select distinct av.val '+
            'from giv_attrib a, giv_attrval av, giv_userprofile p '+
            'where a.id = av.attr_id ' +
            '  and a.name = "country" '+
            '  and av.oid = p.id ' +
            fif(kind in ['s','student'],' and p.kind = "s" ','') +
            fif(kind in ['p','project'],' and p.kind = "p" ','') +
            fif(kind in ['d','donor'],' and p.kind = "d" ','') +
            'order by av.val')
        cursor = connection.cursor()
        cursor.execute(query, [])
        countries = []
        while True:
            try:
                countries.append(str(cursor.fetchone()[0]))
            except: break
        cache.set(cachename, countries, 60)
    return countries

def getRequest(*args, **kwargs):
    request = None
    try:
        request = args[0]
        request = kwargs['request']
    except: pass
    return request

class withUser(object):
    '''decorator to give a view function a user object, or None if not logged in'''
    def __init__(self, f):
        self.__f = f
    def __call__(self, *args, **kwargs):
        request = getRequest(*args, **kwargs)
        user = request.user
        if request.user.is_authenticated():
            kwargs['user']=apparent_user(request)
        else:
            kwargs['user']=None
        return self.__f(*args, **kwargs)

class reqUser(object):
    def __init__(self,f):
        self.__f = f
    def __call__(self, *args, **kwargs):
        request = getRequest(*args, **kwargs)
        user = request.user
        if request.user.is_authenticated():
            kwargs['user']=apparent_user(request)
            kwargs['profile'] = kwargs['user'].get_profile()
            kwargs['obj'] = kwargs['profile'].get_object()
        else:
            kwargs['user']=None
        if kwargs['user'] is None:
            return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
        return self.__f(*args, **kwargs)

class reqDonor(object):
    def __init__(self,f):
        self.__f = f
    def __call__(self, *args, **kwargs):
        request = getRequest(*args, **kwargs)
        user = request.user
        if request.user.is_authenticated():
            kwargs['user']=apparent_user(request)
            kwargs['profile'] = kwargs['user'].get_profile()
            kwargs['donor'] = kwargs['profile'].get_object()
        else:
            kwargs['user']=None
        if kwargs['user'] is None or kwargs['profile'].kind != 'd':
            return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
        return self.__f(*args, **kwargs)

class specUser(object):
    def __init__(self,f):
        self.__f = f
    def __call__(self, *args, **kwargs):
        request = args[0]
        user = request.user
        if request.user.is_authenticated():
            kwargs['user']=apparent_user(request)
        else:
            kwargs['user']=None
        if kwargs['user'] is None:
            return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
        uname = None
        try:
            uname = args[1]
            uname = kwargs['uname']
        except: pass
        print uname
        if uname != kwargs['user'].username:
            return django.http.HttpResponseNotFound(
                "Permission Failure. Are you logged in with an account that can access this?")
        return self.__f(*args, **kwargs)

class adminOnly(object):
    '''needs to be tested'''
    def __init__(self,f):
        self.__f = f
    def __call__(self, *args, **kwargs):
        request = args[0]
        user = request.user
        if request.user.is_authenticated():
            kwargs['user']=apparent_user(request)
        else:
            kwargs['user']=None
        if kwargs['user'] is None:
            return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
        if not user.is_staff:
            return django.http.HttpResponseNotFound(
                "Permission Failure. Only staff can access this page.")
        return self.__f(*args, **kwargs)
