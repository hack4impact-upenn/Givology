


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

from   proj.giv.htmlconv import tagclean, tagunclean, forshow
from   proj.giv.utils import *
from   proj.giv.db import *
from   proj.settings import *


import proj.giv.uform as uform
from   proj.giv.models import *

from proj.giv.viewutils import *
from proj.giv.cache import *





def pubviewimg(request, uname):
    user = User.objects.get(username=uname)
    vuser = apparent_user(request)
    assert user.username == vuser.username or vuser.is_staff
    profile = user.get_profile()
    if 'image' in request.FILES:
	profile.set_image(request.FILES['image'].chunks())
    return render_to_response(tloc+'redirect',{
            'destination':'/~%s/'%(uname)})


def pubview(request, uname):
    '''
    uname refers to the name of the user whose public page is to be
    displayed
    '''
    try:
        user = User.objects.get(username=uname)
        vuser = apparent_user(request)
        assert canviewunapproved(request) or is_approved(user)
    except:
        return django.http.HttpResponseNotFound('username not found')
    profile = user.get_profile()
    if   (get_attr('isanon',profile,'f') == 't' and
          user.username != vuser.username and
          not vuser.is_staff):
        return django.http.HttpResponseNotFound('username not found')
    imageurl = profile.get_image_url(width=206,height=206)
    kind = lower(profile.kind)
    obj = profile.get_object()
    org = None

    confirm_mesg = ''
    if request.POST and vuser.is_staff:
        try:
            admin_action = request.POST['admin_action']
        except:
            return django.http.HttpResponseNotFound('Post exception')
        if admin_action == 'Approve':
            assert kind in ['s','p']
            assert not obj.approved
            obj.approved = True
            obj.save()
            confirm_mesg = '%s has been approved' % profile.name
        elif admin_action == 'Unapprove':
            assert kind in ['s','p']
            assert obj.approved
            d = obj.unapprove()
            obj.save()
            confirm_mesg = '%s has been unapproved.' % profile.name
            confirm_mesg += '\n<br />The following donors have been affected:\n<br />'+'\n<br />'.join([d0.username for d0 in d['donors']])
            confirm_mesg += '\n<br />The following teams have been affected:\n<br />'+'\n<br />'.join([g.slug for g in d['teams']])
        elif admin_action == 'Edit':
            return render_to_response(
                tloc+'redirect', 
                {'destination':'/~%s/editprofile/'%(uname),
                 })
        elif admin_action == 'Save':
            pass
        else:
            raise Hell('unknown approve action')
    try:
        org = obj.org
    except:
        pass
    
    try:
        don = apparent_user(request).get_profile().get_object()
        if isinstance(don, Donor):
            viewerdonor = True
        else:
            viewerdonor = False
    except:
        don = None
        viewerdonor = False
    
    grant = None
    moregrants = []
    grants = []
    try:
        assert kind in ['s','p']
        grants = [g.summary(fif(viewerdonor,don,None))
                  for g in obj.grant_set.all(
                      ).order_by('-created')]
        grant = grants[0]
        moregrants = drop(1,grants)
    except: pass
    if len(moregrants) < 1:
        moregrants = None
    
    edulevel = get_attr('edulevel',profile,default=None)
    try:
        edulevel = {
            '1' :'1st Grade',  '2' :'2nd Grade',
            '3' :'3rd Grade',  '4' :'4th Grade',
            '5' :'5th Grade',  '6' :'6th Grade',
            '7' :'7th Grade',  '8' :'8th Grade',
            '9' :'9th Grade',  '10':'10th Grade',
            '11':'11th Grade', '12':'12th Grade'
            }[edulevel]
    except: pass
    edutype = get_attr('edutype',profile,default=None)
    try:
        edutype = {
            'primary' :'Primary School',
            'middle' :'Middle School',
            'high' :'High School',
            'university' :'University'
            }[edutype]
    except: pass
    #daily per capita income
    dpci = None
    try:
        ai = get_attr('annual_income',profile)
        n = get_attr('numhousehold',profile)
        print float(ai), float(n)
        dpci = ' %.4f '%(float(ai)/(float(n)*365.25))
    except: pass
    partner = None
    try:
        partner = {
            'url':obj.org.profile.url(),
            'name':obj.org.profile.name,
            'img':obj.org.profile.get_image_url(100,50)
            }
    except: pass
    
    attrs = get_attrs(profile)
    try:
        gender = {'m':'Male',
                  'f':'Female',
                  }[profile.gender]
    except:
        gender = False
    
    dbdid = donorbot_donor().id
    teams = None
    subobjs = []
    if   kind in ['s','p']:
        subobjs = [d.profile.summary() for d in obj.get_donors()
                   if d.id != dbdid]
    elif kind in ['d']:
        subobjs = [r.profile.summary() for r in obj.get_donatees()]
        teams = take(5000, obj.donorgroups.all().order_by('name'))
        if len(teams) == 0:
            teams = None
    elif kind in ['o']:
        subobjs = [r.profile.summary() for r in
                   obj.recipient_set.filter(approved=True)]
    
    #for attributes that need special formatting
    for attr in ['about','history','impact','team_credentials',
                 'description','interactions']:
        if attr in attrs and attrs[attr] is not None:
            attrs[attr] = forshow(attrs[attr])
        else:
            attrs[attr] = None
    
    #for attributes that have received html, but should have none.
    for attr in ['extra','future']:
        if attr in attrs and attrs[attr] is not None:
            attrs[attr] = stripshow(attrs[attr])
        else:
            attrs[attr] = None
        
    if 'industry' in attrs and attrs['industry'] is not None:
        try:
            attrs['industry'] = uform.industries[int(attrs['industry'])]
        except: pass

    return render_to_response('profile.html', dictcombine(
            [obj.profile.summary(),
             personaldict(request, uname),
             {'title':'Givology: %s' % (obj.profile.name),
              'kind':kind,
              'isstudent':kind=='s',
              'isdonor':kind=='d',
              'isproject':kind=='p',
              'isorganization':kind=='o',
              'obj':obj,
              'approved':is_approved(user),
              'org':org,
              'grant':grant,
              'grant0':grant,
              'grants':grants,
              'grantcount':len(grants),
              'moregrants':moregrants,
              'attrs':attrs,
              'gender':gender,
              'age':obj.profile.get_age(),
              'edulevel':edulevel,
              'edutype':edutype,
              'choice0':personalchoice(uname),
              'viewerdonor':viewerdonor,
              'image':imageurl,
              'confirm_mesg':confirm_mesg,
              'subobjs':subobjs,
              'subobjs_len':len(subobjs),
              'isviewer':vuser.username==uname,
              'teams':teams,
              'dpci':dpci,
              'partner':partner,
              'uid':user.id,
              'updates':[x.dicttorender() for x in take(5, BlogPost.objects.filter(author=user).order_by('-created'))],
              'cansudo':sudoable(vuser,user),
              }]))

def editprofilemini(request, uname):
    return editprofile(request, uname, ismini=True)

def editprofile(request, uname, ismini=False):
    vuser = apparent_user(request)
    if(vuser.is_anonymous()):
        return django.http.HttpResponse('no permission to edit this!')
    vprofile = vuser.get_profile()
    user = User.objects.get(username=uname)
    profile = user.get_profile()
    kind = profile.kind
    obj = profile.get_object()
    
    canedit = False
    if vuser.username == uname:
        canedit = True
    if vuser.is_staff:
        canedit = True
    if kind in ['s','p'] and vprofile.kind == 'o':
        if obj.org == vprofile.get_object():
            canedit = True
    if not canedit:
        return django.http.HttpResponse('no permission to edit this!')
    
    if   kind == 'd':
        if 'name' not in request.POST:
            return editprofile_donor(request, uname, ismini)
        else:
            return saveprofile_donor(request, uname, ismini)
    elif kind in ['s','p']:
        if 'name' not in request.POST:
            return editprofile_recipient(request, uname)
        else:
            return saveprofile_recipient(request, uname)
    elif kind == 'o':
        if 'name' not in request.POST:
            return editprofile_organization(request, uname)
        else:
            return saveprofile_organization(request, uname)

def editprofile_donor(request, uname, ismini):
    user = User.objects.get(username=uname)
    profile = user.get_profile()
    kind = profile.kind
    obj = profile.get_object()
    
    form = uform.editdonorform(request)
    attrs = get_attrs(profile)
    attrs['email'] = user.email
    attrs['gender'] = profile.gender
    attrs['name'] = profile.name
    attrs['created'] = profile.created
    form.apply(attrs)
    return render_to_response(tloc+fif(ismini,'editdonormini','editdonor'), dictcombine(
            [personaldict(request,uname),
             {'title':'Givology: %s: Editing Profile Information' % (profile.name),
              'choice0':'dashboard',
              'choice1':'edit',
              'profile':profile,
              'obj':obj,
              'form':form.renderhtml(),
              }]))

def saveprofile_donor(request, uname, ismini):
    user = User.objects.get(username=uname)
    profile = user.get_profile()
    kind = profile.kind
    obj = profile.get_object()
    
    form = uform.editdonorform(request)
    form.apply(request.POST)
    o = form.verify()
    if o:
        dict = form.retrieve()
        form.set_attrs(profile)
        user.email = dict['email']
        user.save()
        profile.name = dict['name']
        profile.gender = dict['gender']
        try: profile.created = uform.todatetime(dict['created'])
        except: profile.created = None
        profile.save()
        if ismini:
            return render_to_response(
                tloc+'redirect',
                {'destination':'/~%s/editprofilemini/'%(uname)})
        else:
            return render_to_response(
                tloc+'redirect',
                {'destination':'/~%s/'%(uname)})
    return render_to_response(tloc+fif(ismini,'editdonormini','editdonor'), dictcombine(
            [personaldict(request,uname),
             {'title':'Givology: %s: Editing Profile Information' % (profile.name),
              'profile':profile,
              'obj':obj,
              'form':form.renderhtml(),
              }]))


def saveprofile_recipient(request, uname):
    user = User.objects.get(username=uname)
    profile = user.get_profile()
    kind = profile.kind
    obj = profile.get_object()
    
    form = fif(kind=='s',
               uform.addstudentform(
                   request,grantcount=obj.grant_set.count()),
               uform.addprojectform(
                   request,grantcount=obj.grant_set.count()))
    form.apply(request.POST)
    if form.verify():
        dict = form.retrieve()
        
        name = dict['name']
        if len(dict['fname'])>1:
            name += ' ('+dict['fname']+')'
        profile.name = name
        if 'gender' in dict:
            profile.gender = dict['gender']
        if 'created' in dict:
            profile.created = datetime.datetime.strptime(
                dict['created'],'%Y-%m-%d')
        profile.save()

        
        for i in xrange(obj.grant_set.count()):
            grant = obj.grant_set.all().order_by('created')[i]
            grant.want = int(dict['want_%i'%i])
            grant.save()
            grant.update()
            [f for f in form.subforms
             if take(17,f.label)==take(17,'Grant Information')
             ][i].set_attrs(grant)
        
        form.set_attrs(profile)
        
        return render_to_response(tloc+'redirect', {
                'destination':'/~%s/'% (uname),
                'mesg':'%s edited successfully...' % name })
    else: #if we didn't verify correctly...
        return render_to_response(
            tloc+fif(kind=='s', 'editstudent', 'editproject'),
            dictcombine(
                [personaldict(request, uname),
                 {'title':'Givology: Edit %s' % (profile.name),
                  'form':form.renderhtml(),
                  }])
            )
    


def editprofile_recipient(request, uname):
    user = User.objects.get(username=uname)
    profile = user.get_profile()
    kind = profile.kind
    obj = profile.get_object()
    
    form = fif(kind=='s',
               uform.addstudentform(
                   request,grantcount=obj.grant_set.count()),
               uform.addprojectform(
                   request,grantcount=obj.grant_set.count()))
    attrs = get_attrs(profile)
    p = re.compile('^(?P<name>[^(]+) \((?P<fname>[^)]+)\)$')
    try:
        m = p.match(profile.name)
        name = m.group('name')
        fname = m.group('fname')
    except:
        name = profile.name
        fname = ''

    if 'url' in attrs and attrs['url'][:4] != 'http':
        attrs['url'] = False
    attrs['name'] = name
    attrs['fname'] = fname
    attrs['username'] = uname
    attrs['org'] = str(obj.org.id)
    if kind=='s':
        attrs['gender'] = profile.gender
        attrs['created'] = profile.created
    
    grantdicts = []
    for i in xrange(obj.grant_set.count()):
        grant = obj.grant_set.all().order_by('created')[i]
        grantdicts.append(
            dict([(k+'_%i'%i,v) for k,v in dictcombine([
                get_attrs(grant),
                {'want':str(grant.want),
                 }]).items()]))
    
    form.apply(dictcombine([attrs]+grantdicts))
    
    return render_to_response(
        tloc+fif(kind=='s','editstudent','editproject'),
        dictcombine(
            [personaldict(request,uname),
             {'title':'Givology: %s: Editing Profile Information' % (profile.name),
              'form':form.renderhtml(),
              }]))

def editprofile_organization(request, uname):
    user = User.objects.get(username=uname)
    profile = user.get_profile()
    kind = profile.kind
    obj = profile.get_object()
    
    form = uform.addorganizationform(request)
    attrs = get_attrs(profile)
    attrs['name'] = profile.name
    attrs['created'] = profile.created
    form.apply(attrs)
    return render_to_response(tloc+'editorganization', dictcombine(
            [personaldict(request,uname),
             {'title':'Givology: %s: Editing Profile Information' % (profile.name),
              'profile':profile,
              'obj':obj,
              'form':form.renderhtml(),
              }]))

def saveprofile_organization(request, uname):
    user = User.objects.get(username=uname)
    profile = user.get_profile()
    kind = profile.kind
    obj = profile.get_object()
    
    form = uform.addorganizationform(request)
    form.apply(request.POST)
    o = form.verify()
    if o:
        dict = form.retrieve()
        form.set_attrs(profile)
        profile.name = dict['name']
        try: profile.created = uform.todatetime(dict['created'])
        except: profile.created = None
        profile.save()
        return render_to_response(tloc+'redirect',{'destination':'/~%s/'%(uname)})
    return render_to_response(tloc+'editorganization', dictcombine(
            [personaldict(request,uname),
             {'title':'Givology: %s: Editing Profile Information' % (profile.name),
              'profile':profile,
              'obj':obj,
              'form':form.renderhtml(),
              }]))



def pubviewmap(request, uname, width, height):
    '''
    
    draws the map showing connections between donors and recipients,
    or organizations and recipients.
    
    determines whether it needs to make a new map, and if so, does it,
    then returns the appropriate map.
    
    '''
    try:
        user = User.objects.get(username=uname)
        profile = user.get_profile()
        kind = profile.kind
        obj = profile.get_object()
    except:
        return django.http.HttpResponse('bad username?')
    
    try:
        width = int(width)
        height = int(height)
        assert (width  > 0 and width  <= 1000 and
                height > 0 and height <= 1000 )
    except:
        return django.http.HttpResponse('that size is awkward...')
    
    #base map from wikipedia's page (from nasa originally)
    fname0 = os.path.join(
        IMAGE_DIR,'Equirectangular-projection.jpg')
    #jpg that will result
    imgfname = os.path.join(
        IMAGE_DIR,'user',
        str(user.id)+'__map_%i_%i.jpg'%(width,height))
    #mvg for storing info on how to make it
    mvgfname = os.path.join(
        IMAGE_DIR,'user',
        str(user.id)+'__map_%i_%i.mvg'%(width,height))
    
    #what was the location last used to make a map?
    l0 = get_attr('location_map_recent',profile,default=None)
    
    #when was the most recent donation or whatever that might have
    #altered the map?
    recentact = None
    try:
        if kind == 'd':
            recentact = Paymenttogrant.objects.filter(
                donor=obj).order_by(
                '-created')[0].created
        if kind in ['s','p']:
            recentact = Paymenttogrant.objects.filter(
                grant__rec=obj).order_by(
                '-created')[0].created
        if kind == 'o':
            recentact = datetime.datetime.fromordinal(
                Recipient.objects.filter(
                    org=obj).order_by(
                    '-id')[0].profile.created.toordinal())
    except: pass
    
    #when was the most recent time such a map was made?
    recentimg = None
    try:
        recentimg = datetime.datetime.fromtimestamp(
            os.stat(imgfname)[stat.ST_CTIME])
    except: pass
    
    #if any of these occurs, we need to make a new drawing.
    if  (recentimg is None or
         (recentact is not None and
          recentimg is not None and
          recentact > recentimg) or
         l0 != profile.locationbrief()
         ):
        
        set_attr('location_map_recent',profile.locationbrief(),profile)
        
        print "makin' a map!"
        x = None
        y = None
        xp = None
        
        #if we have a location, keep track of it.
        if profile.latlng():
            x = (180 + profile.lng())*width/360.0
            y = (90.0 - profile.lat())*height/180.0
            xp = ((180 + profile.lng())*width/360.0) + 5.0
        
        linkends = []
        linksto = []
        if kind == 'd': linkends = obj.get_donatees()
        if kind in ['s','p']: linkends = obj.get_donors()
        if kind == 'o': linkends = obj.get_recipients()
        
        #create control points for each connection
        for d in linkends:
            if d.profile.latlng() is not None:
                nx = (180+d.profile.lng())*width/360.0
                ny = (90.0-d.profile.lat())*height/180.0
                if x is not None:
                    #if both have latitude/longitude,
                    # then prepare the curve.
                    mx = (x+nx)/2.0
                    my = (((((abs(x-nx)*1.0/width)*2)+1) *
                           (((y+ny)/2.0)-(height/2.0))) +
                          (height/2.0))
                else: mx = None; my = None
                linksto.append({
                        'x':nx,  'y':ny,
                        'mx':mx, 'my':my,
                        'xp':nx+5.0,
                        })
        
        #make mvg code; write it to the file
        mvg = render_to_string(tloc+'map.mvg',{
                'mapimgname':fname0,
                'y':y, 'x':x, 'xp':xp,
                'width':width,
                'height':height,
                'linksto':linksto,
                })
        open(mvgfname,'w').write(mvg)
        
        #imagemagick uses the mvg to make the jpg
        os.spawnv(os.P_WAIT, '/usr/bin/convert',
                  ['convert','-strip','-quality','65',
                   mvgfname, imgfname])
    
    #write output as a jpeg (i wish i could pipe this, rather than
    #read the whole thing into memory then write it out)
    r = django.http.HttpResponse(mimetype='image/jpeg')
    r.write(open(imgfname,'r').read())
    return r


