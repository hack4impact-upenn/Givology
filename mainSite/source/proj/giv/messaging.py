

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


import json


from   proj.giv.consts import *

import proj.giv.captcha as captcha
from   proj.giv.htmlconv import isemailvalid, tagclean, tagunclean, forshow
from   proj.giv.utils import *
from   proj.giv.db import *
from   proj.settings import *

import proj.giv.uform as uform
from   proj.giv.models import *

from proj.giv.cache import *
from proj.giv.viewutils import *

@reqUser
def composeimg(request, user, profile, obj):
    resize_x = 600
    resize_y = 1000
    try:
        resize_x = int(request.POST['resize_x'])
        resize_y = int(request.POST['resize_y'])
    except: pass
    if resize_x > 600:
        resize_x = 600
    if resize_y > 1000:
        resize_y = 1000
    resize_s = str(resize_x)+'x'+str(resize_y)+'>'
    images = []
    try:
        images = request.POST['images'].split(',')
    except: pass
    imageappend = None
    if 'image' in request.FILES:
        fname0 = str(user.id) + '_' + str(random.randint(0,(1<<64)-1)) + '.jpg'
        fname = os.path.join(IMAGE_DIR, 'user', fname0)
        destination = open(fname, 'wb+')
    	for chunk in request.FILES['image'].chunks():
	        destination.write(chunk)
	        os.spawnv(os.P_WAIT, '/usr/bin/convert',
                	['convert','-geometry',resize_s,
                   	'-strip','-quality','70',
                   	fname, fname])
        	images += ['/images/user/'+fname0]
        	imageappend = '<img src=\\"%s\\">' % ('/images/user/'+fname0)
		destination.close()
    images = [s for s in images if len(s) > 5]
    return render_to_response(tloc+'composeimg',
                              {'images':images,
                               'images_h':','.join(images),
                               'imageappend':imageappend,
                               'resize_x':resize_x,
                               'resize_y':resize_y,
                               })
        
class IMsg():
    def __init__(self, kind=None, id=None, body = '', subject = '', to = '', parent = None, tags = '', request=None, mode='compose', user=None):
        self.kind    = kind
        self.id      = id
        self.rbody   = None
        self.body    = body
        self.subject = subject
        self.to      = to
        self.parent  = parent
        self.tags    = tags
        if request is not None:
            if user is None:
                user = apparent_user(request)
            r = request.REQUEST
            
            try: self.kind = r['type']
            except: pass
            
            try: self.parent = int(r['parent'])
            except: pass
            
            try:
                try:
                    self.subject = tagclean(toutf(urlsafe_b64decode(r['bsubject'])))
                except:
                    self.subject = tagclean(str(r['subject']))
            except: pass
            
            try:
                try:
                    self.rbody = tagclean(toutf(urlsafe_b64decode(r['brbody'])))
                except:
                    self.rbody = tagclean(str(r['body']))
                self.body = forshow(self.rbody)
            except: pass
            
            try:
                print r['to']
                self.rto = [a for a in
                            [a.strip() for a in
                             tagclean(str(r['to'])).split(',')]
                            if (''.join(take(5,a)) == 'team-'
                                or User.objects.filter(
                                    username=a).count()==1
                                or a in ['all_donors','all_staff']
                                )
                            ]
                print 'rto ' + str(self.rto)
                self.to = ', '.join(self.rto)
            except: pass
            
            try:
                self.rtags = parsetags(tagclean(str(r['tags'])),
                                       user=request.user)
                self.rtags.sort()
                self.tags = tags2str(self.rtags).strip()
            except: pass
            
            try: self.id = int(r['id'])
            except: pass
            if ( self.id is not None and mode == 'compose'
                 and self.kind in ['blogpost','comment']):
                post = BlogPost.objects.get(id=self.id)
                assert user == post.author
                self.subject = post.subject
                self.body = post.text
                self.tags = tags2str([t.tag for t in post.tags.all()])
        if len(self.subject) < 1 and mode != 'compose':
            self.subject = 'No Subject'
        self.author = user
        assert self.kind in ['comment','message','blogpost',None]
    def bsubject(self):
        return urlsafe_b64encode(toutf(self.subject).encode('utf-8'))
    def brbody(self):
        return urlsafe_b64encode(toutf(self.rbody).encode('utf-8'))
    def blogpost(self):
        return {
            'uname':self.author.username,
            'name':self.author.get_profile().name,
            'url':None,
            'subject':self.subject,
            'tags':self.tags,
            'text':self.body,
            'parent':self.parent,
            'parenturl':None,
            'numcomments':0,
            }
    def message(self):
        return {
            'from':self.author.username,
            'to':self.to,
            'subject':self.subject,
            'body':self.body,
            }
    def recvrs(self):
        """
        returns a final list of usernames to send to (for example,
        expanding things like all_donors)
        """
        recvrs = []
        for recvr in self.rto:
            if recvr == 'all_donors' and self.author.is_admin:
                recvrs += [d.profile.user.username 
                           for d in Donor.objects.all()]
            elif recvr == 'all_staff' and self.author.is_admin:
                recvrs += [u.username for u in
                           User.objects.filter(is_staff=True)]
            elif ''.join(take(5,recvr)) == 'team-':
                try:
                    team = DonorGroup.objects.get(
                        slug=''.join(drop(5,recvr)))
                    assert team.can_message(self.author)
                    recvrs += [d.profile.user.username
                               for d in team.donors.all()]
                except: pass
            else:
                recvrs += [recvr]
        recvrs = removeduplicates(recvrs)
        recvrs = [uname for uname in recvrs
                  if User.objects.filter(
                      username=uname).count() > 0]
        return recvrs
    def commit(self,approved=True):
        """
        when done editing/composing, commits.
        """
        print 'commit imsg!'
        if self.kind in ['comment','blogpost']:
            return self.bpcommit(approved=approved)
        else:
            return self.msgcommit()
    def msgcommit(self):
        recvrs = self.recvrs()
        message = send_message(
            self.author, self.recvrs(), self.subject, self.rbody)
        return (message,
                '/~%s/outbox/%i' % (self.author.username,
                                    message.id)
                )
    def bpcommit(self,approved=True):
        post = None
        if self.id is None:
            post = BlogPost(iscomment=(self.kind=='comment'),
                            author=self.author,
                            subject=self.subject,
                            text=self.rbody,
                            approved=approved)
            print 'made new id-less post'
        if self.id is not None:
            post = BlogPost.objects.get(id=self.id)
            assert self.author == post.author
            post.subject = self.subject
            post.text = self.rbody
            post.approved = approved
            for t in post.tags.all():
                t.delete()
        post.save()
        for tag in self.rtags:
            BlogPostTag(blogpost=post,tag=tag).save()
        if post.iscomment:
            if self.id is None and post.getspamclass() == 'ham':
                print 'adding as child'
                parent = BlogPost.objects.get(id=self.parent)
                print 'got parent'
                parent.children.add(post)
                print 'added'
                if islive:
                    self.commentmsg(post, parent)
        if ( self.id is None and
             (not post.iscomment) and
             self.author.get_profile().kind in ['s','p'] and
             post.approved):
            recupdate(post)
        print 'done with bpcommit'
        return (post, post.url())
    def commentmsg(self, post, parent):
        """
        sends a message to the author of the parent, notifying that a
        comment has been created.
        
        """
        body = tagclean(
            render_to_response(
                'letters/newcomment.html',
                {'reader':parent.author.get_profile().name,
                 'commenterurl':self.author.get_profile().url(),
                 'commenter':self.author.get_profile().name,
                 'purl':parent.url(),
                 'ptitle':parent.subject,
                 'curl':post.url(),
                 'commenttext':self.rbody,
                 }).content)
        
        send_message(
            User.objects.get(username='givbot'),
            [parent.author],
            'New Comment',
            body, approved=True)
        

def recupdate(post):
    """
    adds this to the list of updates for each person who donated
    to the author.
    """
    if not post.approved:
        return False
    profile = post.author.get_profile()
    rec = profile.get_object()
    
    tolist = [User.objects.get(id=id) for id in
              set([donor.profile.user.id
                   for donor in rec.get_donors()] +
                  [a.id for a in 
                   User.objects.filter(is_staff=True)])
              ]
    
    body = tagclean(
        render_to_response(
            fif(profile.kind=='s',
                'letters/bloggedstudent.html',
                'letters/bloggedproject.html'),
            {'name':profile.common_name(),
             'fullname':profile.name,
             'url':profile.url(),
             'blogurl':profile.blogurl(),
             'partnername':rec.org.profile.common_name(),
             'partnerurl':rec.org.profile.url(),
             }).content)
    
    for u in tolist:
        invalidatecache('updatecounts|'+u.username)
        send_message(
            User.objects.get(username='givbot'),
            [u],
            fif(profile.kind == 's',
                'Update on your Givology Student!',
                'Update on your Givology Project!'),
            body,
            approved=True)
    return True


def compose(request, captcha_result = None):
    """
    The compose page.
    
    The process is as follows:
    user visits compose page
    submits to preview page
    submits to composed page (which then commits).
    
    """
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    try:
        m = IMsg(request=request, mode='compose', user=user)
    except:
        print gettraceback()
        return django.http.HttpResponseNotFound('Error parsing http GET. \n\nExample: http://www.givology.org/compose?type=message')
    
    p = request.user.get_profile()
    need_captcha = not p.has_completed_captcha()
    captcha_html = False
    if need_captcha:
        captcha_html = captcha.new_captcha_html(captcha_result)
    
    return render_to_response(tloc+'compose', dictcombine(
            [personaldict(request, user.username, user),
             {'title':"Givology: Compose",
              'm':m,
              'captcha_html':captcha_html,
              }]))

def previewjson(request):
    return preview(request, usejson=True)

def preview(request, usejson=False):
    """
    note: json currently removed
    """
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})

    user = apparent_user(request)
    try:
        m = IMsg(request=request, mode='preview', user=user)
    except:
        print gettraceback()
        return django.http.HttpResponseNotFound('Error... please contact site admins if problem persists.')
    
    p = request.user.get_profile()
    need_captcha = not p.has_completed_captcha()
    if need_captcha:
        captcha_result = captcha.check_captcha(request)
        if captcha_result is None or not captcha_result.is_valid:
            return compose(request, captcha_result)
        else:
            p.has_completed_captcha(True)
    
    return render_to_response(tloc+'preview', dictcombine(
            [personaldict(request, user.username, user),
             {'title':"Givology: Preview",
              'm':m,
              'post':m.blogpost(),
              'msg':m.message(),
              }]))

def composed(request):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    user = apparent_user(request)
    try:
        m = IMsg(request=request, mode='composed', user=user)
    except:
        print gettraceback()
        return django.http.HttpResponseNotFound('Error... please contact site admins if problem persists.')
    
    p = request.user.get_profile()
    need_captcha = not p.has_completed_captcha()
    if need_captcha:
        captcha_result = captcha.check_captcha(request)
        if captcha_result is None or not captcha_result.is_valid:
            return compose(request, captcha_result)
        else:
            p.has_completed_captcha(True)
    
    asdf = request.POST.get('asdf')
    robospammed = asdf is not None and len(asdf) > 0
    approved = (user.get_profile().kind == 'd'
                or (user.olduser is not None and user.olduser.is_staff))
    #note: non-donors may only make blog posts, not comments or messages
    if (not robospammed and
        (user.get_profile().kind == 'd' or m.kind == 'blogpost')):
        obj, url = m.commit(approved=approved)
    else: url='/'
    if m.kind == "comment":
        url = BlogPost.objects.get(id=m.parent).url()
    return render_to_response(tloc+'redirect',{
            'destination':url})


def message_view(request, uname, message_id, choice1):
    if not request.user.is_authenticated():
        return render_to_response(tloc+'redirect', {
                'destination':'/login/'})
    u = apparent_user(request)
    if u.username != uname:
        return django.http.HttpResponseNotFound('rawr!')
    messages = Message.objects.filter(id=message_id)
    if (messages.count() != 1):
        return django.http.HttpResponseNotFound('Message not found.')
    message = messages[0]
    tos = message.to.all()
    if u not in tos and u != message.fr:
        return django.http.HttpResponseForbidden('Access to this message denied!')
    return render_to_response(tloc+'message', dictcombine(
            [personaldict(request, uname),
             {'title':'Message: %s' %(message.subject),
              'msg':message.dicttorender(),
              'choice0':'My Account',
              'choice1':choice1,
              }]))
    
def message_view_email(message, u):
    #message = Message.objects.get(id=id)
    tos = message.to.all()
    return render_to_string(tloc+'smallmessage',
             {'title':'Message: %s' %(message.subject),
              'msg':message.dicttorender(),
              'link':'https://www.givology.org/~%s/inbox/%i/'%(u.username,message.id),
              'bgcolor':'#fff',
              })

def message_out(request, uname, message_id):
    return message_view(request, uname, message_id, 'Outbox')

def message_in(request, uname, message_id):
    return message_view(request, uname, message_id, 'Inbox')








def send_message(fr, to, subject, body, approved=None):
    if approved is None:
        obj = fr.get_profile().get_object()
        if isinstance(obj, Recipient) and obj.postneedapproval:
            approved = False
        else:
            approved = True
    
    message = Message(fr=fr,
                      subject=subject,
                      text=body,
                      approved=approved)
    message.save()
    id = int(message.id)
    s=None
    rs = set()
    for recvr in to:
        if not isinstance(recvr, User):
            u = User.objects.get(username=recvr)
            un= recvr
        else:
            u = recvr
            un = recvr.username
        if un in rs:
            continue
        rs.add(un)
        message.to.add(u)
        if   (u.email and isemailvalid(u.email) and
              get_attr('message_email', u, 'y')=='y' and
              islive):
            s = sendmail(
                fr='giv_updates@givology.org',
                to=u.email,
                subject='Givology Message: '+subject,
                body=('\nYou have a message to your Givology account from %s\n\n' % (message.fr.username) +
                      'https://www.givology.org/~%s/inbox/%i/\n\n' % (u.username, message.id) +
                      ('-'*70) + '\n\n' +
                      tagunclean(body)),
                server=s,
                htmlbody=addhttproot(message_view_email(message,u))
                )
        invalidatecache('updatecounts|'+un)
    message.save()
    return message



@adminOnly
def approvepost(request, user):
    preapproved = True
    try:
        admin_action = request.POST['admin_action']
        assert admin_action == 'Approve'
        print request.POST['postid']
        post = BlogPost.objects.get(id=int(request.POST['postid']))
        print post.id
        preapproved = post.approved
        post.approved = True
        post.save()
    except:
        import sys
        print "Unexpected error:", sys.exc_info()
        return django.http.HttpResponseNotFound('Post error...')
    if not preapproved:
        recupdate(post)
    return django.http.HttpResponse('Post approved')

@adminOnly
def markblogspam(request, user):
    try:
        post = BlogPost.objects.get(id=int(request.POST['postid']))
        post.setspamclass('spam',train=True)
    except:
        import sys
        print "Unexpected error:", sys.exc_info()
        return django.http.HttpResponseNotFound('Post error...')
    return django.http.HttpResponse('Post marked as Spam')

@adminOnly
def markblogham(request, user):
    try:
        post = BlogPost.objects.get(id=int(request.POST['postid']))
        post.setspamclass('ham',train=True)
    except:
        import sys
        print "Unexpected error:", sys.exc_info()
        return django.http.HttpResponseNotFound('Post error...')
    return django.http.HttpResponse('Post marked as Ham')


@adminOnly
def donormessages(request, user):
    '''
    listing messages from donors to students/projects

    (rudimentary version...)
    '''

    select = 'distinct m.id'
    froms = ['giv_message m',
             'giv_message_to mt',
             'giv_userprofile dp',
             'giv_userprofile rp',
             'giv_recipient r',
             ]
    wheres = ['m.id = mt.message_id',
              'm.fr_id    = dp.user_id ',
              ' mt.user_id = rp.user_id',
              '(rp.kind = "s" or rp.kind = "p")',
              'dp.kind = "d"',
              'r.profile_id = rp.id',
              ]
    orderby = 'm.created asc'
    values=[]


    orguname = ''
    orgid = None
    if 'org' in request.REQUEST:
        orguname = request.REQUEST['org']
        if len(orguname) > 0:
            orgid = User.objects.get(
                username=orguname).get_profile().get_object().id
            wheres.append('r.org_id = %i'%orgid)
    
    before = 'YYYY-MM-DD'
    try:
        inp = tagclean(request.REQUEST['before'])
        print inp
        before = datetime.datetime.strptime(
            inp,'%Y-%m-%d')
        print before
        values.append(before)
        wheres.append('m.created < ?')
        before = inp
    except: pass
    
    after = 'YYYY-MM-DD'
    try:
        inp = tagclean(request.REQUEST['after'])
        after = datetime.datetime.strptime(
            inp,'%Y-%m-%d')
        values.append(after)
        wheres.append('m.created > ?')
        after = inp
    except: pass
    
    orgs = ([{'uname':'','name':''}] +
            [o.summary() for o in
             UserProfile.objects.filter(kind='o')]
            )
    for org in orgs:
        if org['uname'] == orguname:
            org['selected']=True
    

    
    result = runquery(mkquery(select,froms,wheres,orderby),
                      r=None, values=values)
    l = []
    for e in result:
        l.append(Message.objects.get(id=e).dicttorender())
    #print l

    return render_to_response(tloc+'donormessages', dictcombine(
            [maindict(request),
             {'title':"Givology: Donor Messages",
              'messages':l,
              'nummessages':len(l),
              'orgs':orgs,
              'before':before,
              'after':after,
              's':fif(len(l)==1,'','s'),
              }]))
