

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
from   django.db import connection, backend
from   django.db import models
import django.http
from   django.shortcuts import render_to_response
from   django.template.defaultfilters import slugify
from   django.template.loader import render_to_string
from   django.utils import feedgenerator


from   proj.giv.consts import *

from   proj.giv.htmlconv import tagclean, tagunclean, forshow, isemailvalid
from   proj.giv.utils import *
from   proj.giv.db import *
from   proj.settings import *

import proj.giv.uform as uform
from   proj.giv.models import *


from proj.giv.viewutils import *


import proj.giv.messaging as messaging

def teams(request):
    '''
    giving teams page
    '''
    user = apparent_user(request)
    error = None
    newteam = None
    name = None
    private = False
    slug = None
    #todo: show list of teams
    
    
    teams = DonorGroup.objects.all()

    name = None
    if 'name' in request.GET:
        name = request.GET['name']
        for n in name.split():
            n = n.strip()
            teams = teams.filter(name__icontains=n)
    category = None
    if 'category' in request.GET:
        category = request.GET['category']
        teams.filter(category=category)
    location = None
    if 'location' in request.GET:
        location = request.GET['location']
        for n in location.split():
            n = n.strip()
            teams = teams.filter(location__icontains=n)
    orderby_ = None
    orderby='-amtdonated'
    if 'orderby' in request.GET:
        orderby_ = request.GET['orderby']
        if   orderby_ == 'Amount Donated':
            orderby = '-amtdonated'
        elif orderby_ == 'Number of Members':
            orderby = '-numdonors'
        elif orderby_ == 'Name':
            orderby = 'name'
        else:
            orderby_ = None
    teams = teams.order_by(orderby)
    
    blog = paginate(request, teams, count0=10, width=5)
    for obj in blog['objects']:
        obj.image_url = obj.get_image_url(width=100,height=68)
    #blog['objects'] = [p.summary() for p in blog['objects']]
    
    teams = teams.order_by('numdonors')
    return render_to_response(tloc+'teams', dictcombine(
            [maindict(request),
             {'choice0':'Community',
              'teams':teams,
              'blog':blog,
              'name':name,
              'category':category,
              'location':location,
              'orderby':orderby_,
              }]))

def team_modify(team, dict):
    
    if 'category' in dict:
        team.category = dict['category']
    if 'loc' in dict:
        team.location = dict['loc']
    if 'because' in dict:
        team.whydonate = ''.join(take(100,dict['because']))
    if 'about' in dict:
        set_attr('about',dict['about'],team)
    
    if   'admin' in lower(dict['join']):
        team.worldjoin    = False
        team.memberinvite = False
        team.admininvite  = True
    elif 'member' in lower(dict['join']):
        team.worldjoin    = False
        team.memberinvite = True
        team.admininvite  = True
    elif 'anyone' in lower(dict['join']):
        team.worldjoin    = True
        team.memberinvite = True
        team.admininvite  = True
    
    if   'nonmembers' in lower(dict['messaging']):
        team.worldemail  = True
        team.memberemail = True
        team.adminemail  = True
    elif 'members' in lower(dict['messaging']):
        team.worldemail  = False
        team.memberemail = True
        team.adminemail  = True
    elif 'admin' in lower(dict['messaging']):
        team.worldemail  = False
        team.memberemail = False
        team.adminemail  = True
    
    if   'nonmembers' in lower(dict['blogging']):
        team.worldblog  = True
        team.memberblog = True
        team.adminblog  = True
    elif 'members' in lower(dict['blogging']):
        team.worldblog  = False
        team.memberblog = True
        team.adminblog  = True
    elif 'admin' in lower(dict['blogging']):
        team.worldblog  = False
        team.memberblog = False
        team.adminblog  = True

    amt = 0
    try: amt = int(dict['cause_amt'])
    except: print 'failed to read cause_amt'
    team.set_cause_amt(amt)
    
    return team

def team_create(request):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    v = False
    user = apparent_user(request)
    profile = user.get_profile()
    donor = profile.get_object()
    form = uform.donorgroupform(request, 'Founding')
    if profile.kind != 'd':
        return django.http.HttpResponseForbidden(
            'This page is for donors only.')
    if request.method=='POST':
        form.apply(request.POST)
        v = form.verify()
        dict = form.retrieve()
        if v:
            name = dict['name'].strip()
            slug = ''.join(take(TAG_MAX_LENGTH-5,slugify(name)))
            try:
                g = DonorGroup.objects.get(slug=slug)
                return django.http.HttpResponse(
                    'Team name not unique enough; '+
                    'try a different one')
            except: pass
            newteam = DonorGroup(
                slug = slug,
                name = name)
            newteam.save()
            team_modify(newteam, dict)
            newteam.save()
            newteam.add_admin(donor)
            form.set_attrs(newteam)
            return render_to_response(
                tloc+'redirect', 
                {'destination':'/teams/%s/'%slug})
    return render_to_response(tloc+'teamedit',dictcombine(
            [maindict(request),
             {'title':'Givology: Register',
              'choice0':'Community',
              'form':form.renderhtml(),
              }]))

def team_edit(request, slug):
    v = False
    user = apparent_user(request)
    team = None
    try:
        team = DonorGroup.objects.get(slug=slug)
    except:
        return django.http.HttpResponseNotFound(
            'No team with that name...?')
    if not team.is_admin(user):
        return django.http.HttpResponseForbidden(
            "You need to be the team admin to edit a team's information")
    form = uform.donorgroupform(request, 'Editing')
    form.apply({
        'loc':team.location,
        'category':team.category,
        'because':team.whydonate,
        'about': get_attr('about',team,default=''),
        'private':team.private,
        'join':get_attr('joinprivs',team,default='blah'),
        'messaging':get_attr('messageprivs',team,default='blah'),
        'blogging':get_attr('blogprivs',team,default='blah'),
        'cause_amt':team.get_cause_amt(),
        })
    if form is None:
        return django.http.HttpResponseNotFound(
            'This page is for donors only.')
    if request.method=='POST':
        form.apply(request.POST)
        v = form.verify()
        dict = form.retrieve()
        if v:
            team_modify(team, dict)
            form.set_attrs(team)
            team.save()
            return render_to_response(
                tloc+'redirect', 
                {'destination':'/teams/%s/'%slug})
    return render_to_response(tloc+'teamedit',dictcombine(
            [maindict(request),
             {'title':'Givology: Register',
              'choice0':'Community',
              'form':form.renderhtml(),
              }]))

def invite_code(slug, inviter_uname, invitee_uname):
    return urlsafe_b64encode(
        sha.new(SECRET_KEY + slug + inviter_uname + invitee_uname).digest())

def team_join(request, slug):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    if user.get_profile().kind != 'd':
        return django.http.HttpResponseForbidden(
            'This page is for donors only.')
    code = None
    inviter = None
    try:
        team = DonorGroup.objects.get(slug=slug)
    except:
        return django.http.HttpResponseNotFound(
            'No team with that name!')
    if team.is_member(user):
        return render_to_response(tloc+'redirect', 
            {'destination':'/teams/%s/'%slug,
             'msg':'You are already a member!'})
    if team.worldjoin:
        team.join(user.get_profile().get_object())
        return render_to_response(
            tloc+'redirect', 
            {'destination':'/teams/%s/'%slug,
             'mesg':'Successfully joined!'})
    code = ''
    inviter = ''
    try: code = request.REQUEST['code']
    except: return django.http.HttpResponse(
        'Missing invitation code')
    try: inviter = request.REQUEST['inviter']
    except: return django.http.HttpResponse(
        "Missing inviter")
    if not (invite_code(slug, inviter, user.username) == code or
            invite_code(slug, inviter, user.email)    == code):
        return django.http.HttpResponse(
            'Invalid invitation code: the invitation must match the email you used to sign up or your givology username.  Contact the person who invited you to clarify this information so they can send you a new invitation.')
    
    #todo: clean this part up, and add more error handling
    inviter = User.objects.get(username=inviter)
    inviter = inviter.get_profile()
    assert inviter.kind == 'd'
    inviter = inviter.get_object()
    
    if team.can_invite(inviter):
        team.join(user.get_profile().get_object())
        return render_to_response(
            tloc+'redirect', 
            {'destination':'/teams/%s/'%slug,
             'mesg':'Successfully joined!'})
    else:
        return django.http.HttpResponse(
            'Inviter lacks permission to invite you.')
    print "how did i get here?"
    return render_to_response(tloc+'teamjoin',dictcombine(
            [maindict(request),
             {'title':'Givology: Register',
              'choice0':'Community',
              'code':code,
              'inviter':inviter,
              'team':team,
              }]))

def team_invite(request, slug):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    team = None
    try:
        team = DonorGroup.objects.get(slug=slug)
    except:
        return django.http.HttpResponseNotFound(
            'No donor team with that identifier found...')
    if not team.can_invite(user):
        return django.http.HttpResponseForbidden(
            'You do not have permission to invite to this team.')
    recipients = []
    msg = ''
    try:
        recipients = [a.strip() for a in
                      request.REQUEST['recipients'].split(',')
                      if isemailvalid(a.strip())]
    except: pass
    print recipients
    try:
        msg = request.REQUEST['msg']
    except: pass
    
    for invitee in recipients:
        code = invite_code(team.slug,user.username,invitee)
        link = 'https://www.givology.org/teams/%s/join/?inviter=%s&code=%s' % (team.slug, user.username, code)
        sendmail(fr='giv_updates@givology.org',
                 to=invitee,
                 subject='Givology Giving Team Invitation',
                 body="",
                 htmlbody = render_to_response(
                     tloc+'letters/teaminvite.html',
                     {'inviterurl':'https://www.givology.org'+user.get_profile().url(),
                      'invitername':user.get_profile().name,
                      'teamname':team.name,
                      'msg':msg,
                      'link':link,
                      }).content)
    return render_to_response(
        tloc+'redirect', 
        {'destination':'/teams/%s/' % (team.slug),
         'msg':'Your friends have been invited! Returning to the team page...',
         })

def team_blog(request, slug):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    team = None
    try:
        team = DonorGroup.objects.get(slug=slug)
    except:
        return django.http.HttpResponseNotFound(
            'No donor team with that identifier found...')
    if not team.can_blog(user):
        return django.http.HttpResponseForbidden(
            'You do not have permission to blog on behalf of this team.')
    return render_to_response(
        tloc+'redirect', 
        {'destination':'/compose/?type=blogpost&tags=team %s'%team.slug,
         })

def team_message(request, slug):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    team = None
    try:
        team = DonorGroup.objects.get(slug=slug)
    except:
        return django.http.HttpResponseNotFound(
            'No donor team with that identifier found...')
    if not team.can_message(user):
        return django.http.HttpResponseForbidden(
            'You do not have permission to message this team.')
    return render_to_response(
        tloc+'redirect', 
        {'destination':'/compose/?type=message&to=team-%s'%team.slug,
         })

@reqDonor
def givecause(request, slug, user, profile, donor):
    try: team = DonorGroup.objects.get(slug=slug)
    except: return django.http.HttpResponse('no such team')
    try:
        amount = int(request.POST['amt'])
        assert amount > 0
    except: return django.http.HttpResponse(
        'Amount to give must be a whole number greater than zero.')
    p = profile
    d = donor
    if amount > d.have_informal():
        return django.http.HttpResponse('Insufficient funds')
    while 1:
        r = randint56()
        if GiftCert.objects.filter(key=r).count()==0:
            break
    gc = GiftCert(
        creator=d,
        receiver=team.admins.all()[0],
        key=str(r),
        amount=amount)
    gc.save()
    set_attr('for_cause',slug,gc)
    return render_to_response(
        tloc+'redirect',
        {'destination':team.url(),'msg':'Gift given!'}
        )
    

def teamview(request, slug):
    user = apparent_user(request)
    team = None
    try:
        team = DonorGroup.objects.get(slug=slug)
    except:
        return django.http.HttpResponseNotFound(
            'No donor team with that identifier found...')
    
    posts = BlogPost.objects.filter(tags__tag='team %s'%team.slug)
    if not canviewunapproved(request):
        posts = posts.filter(approved=True)
    posts = posts.order_by('-created')
    blog = paginate(request, posts, count0=10, width=5)
    blog['posts'] = [p.dicttorender() for p in blog['objects']]
    blog['url'] = '/teams/%s/'%team.slug
    
    whydonate = False
    if len(team.whydonate) > 5:
        whydonate = forshow(team.whydonate)
    about = get_attr('about',team,default=None)
    if about is not None:
        about = forshow(about)
    admins = set([d.profile.id for d in team.admins.all()])
    members = set([d.profile.id for d in team.donors.all()]).difference(admins)
    return render_to_response(tloc+'teamview', dictcombine(
            [maindict(request),
             {'choice0':'Community',
              'team':team,
              'admins':[UserProfile.objects.get(id=i).summary()
                         for i in admins],
              'members':[UserProfile.objects.get(id=i).summary()
                         for i in members],
              'caninvite':team.can_invite(user),
              'canblog':team.can_blog(user),
              'canmessage':team.can_message(user),
              'canedit':team.is_admin(user),
              'ismember':team.is_member(user),
              'canjoin':(team.worldjoin and (not team.is_member(user))),
              'whydonate':whydonate,
              'about':about,
              'blog':blog,
              'image':team.get_image_url(width=250,height=400),
              'is_cause':team.is_cause(),
              'cause_amt':team.get_cause_amt(),
              'cause_cur':team.get_cause_cur(),
              }]))

def team_addadmin(request, slug):
    team = DonorGroup.objects.get(slug=slug)
    user = apparent_user(request)
    assert(team.is_admin(user))
    u = None
    try:
        u = User.objects.get(
            username=request.POST['uname'])
    except:
        return django.http.HttpResponse(
            'the username "%s" could not be found; are you sure you are using the username (what they use to log in) and not their real name?'%request.POST['uname'])
    team.add_admin(u)
    
    #todo: have better response.
    return django.http.HttpResponse('done.')


def teamviewimg(request, slug):
    user = apparent_user(request)
    team = None
    try:
        team = DonorGroup.objects.get(slug=slug)
    except:
        return django.http.HttpResponseNotFound(
            'No team with that name...?')
    if not team.is_admin(user):
        return django.http.HttpResponseForbidden(
            "You need to be the team admin to edit a team's image")
    
    if 'image' in request.FILES:
        team.set_image(request.FILES['image']['content'])
    return render_to_response(tloc+'redirect',{
            'destination':'/teams/%s/'%(team.slug)})
