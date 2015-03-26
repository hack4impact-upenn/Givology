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
from   django.views.decorators.cache import cache_page


from   proj.giv.consts import *

from   proj.giv.htmlconv import tagclean, tagunclean, forshow, stripshow
from   proj.giv.utils import *
from   proj.giv.db import *
from   proj.giv.cache import *
from   proj.settings import *
import proj.giv.spam as spam



# Create your models here.

class Constants(models.Model):
    class Admin: pass
    name = models.CharField(unique=True,max_length=40)
    value = models.TextField(default='')
    def __unicode__(self):
        return unicode(self.name)+u' : '+unicode(self.value)
def constant(name,default=''):
    return withcache('constants|'+name+'|default:'+default,
                     _constant,
                     {'name':name,'default':default},
                     duration=10*60)
def _constant(d):
    try: return Constants.objects.get(name=d['name']).value
    except: return d['default']
def constants():
    return withcache('allconstants',
                     _constants,
                     {}, duration=10*60)
def _constants(a):
    l = Constants.objects.all()
    d = {}
    for c in l:
        d[c.name] = c.value
    return d
#class Constant():
#    def __getitem__(self,a): return constant(a)


class UserProfile(models.Model):
    """
    To create a new user:
    > u = User.objects.create_user(username, email, raw_password)
    > u.save()
    > p = UserProfile(user=u) # also include non-blank fields
    > p.save()
    
    To access profile information
    > u.get_profile().name
    """
    class Admin: pass
    # Account Meta
    user = models.ForeignKey(User, unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    kind = models.CharField(max_length=1, choices=KIND_CHOICES)
    # Profile 
    #pic = models.ImageField(upload_to='') # Todo: Choose upload path
    name = models.CharField(max_length=NAME_MAX)
    created = models.DateField(null=True, blank=True) #for birth or incorporation date
    def url(self):
        return '/~' + self.user.username + '/'
    def edit_url(self):
        return self.url() + 'editprofile/'
    def blog_url(self):
        return self.url() + 'blog/'
    def blogurl(self):
        return '/~' + self.user.username + '/blog/'
    def __unicode__(self):
        return self.name
    def isanon(self):
        if get_attr('isanon',self,'f') == 't':
            return True
        return False
    def common_name(self):
        if self.name.find('(') > 0:
            return self.name[:self.name.find('(')].strip()
        return self.name
    def get_age(self):
        if self.created is None or self.kind == 'o':
            return None
        today = datetime.date.today()
        years = today.year - self.created.year
        if (today.month, today.day) < (self.created.month, self.created.day):
            years -= 1
        return years
    def get_object(self):
        if   lower(self.kind) in ['s','student','p','project']:
            return Recipient.objects.get(profile=self)
        elif lower(self.kind) in ['d','donor']:
            return Donor.objects.get(profile=self)
        elif lower(self.kind) in ['o','organization']:
            return Organization.objects.get(profile=self)
        raise hell #user's kind incorrect...
        return
    def base_image(self):
        count = get_attr('imgupcount',self, default = None)
        oldfile = os.path.join(IMAGE_DIR,'user',unicode(self.user.id))
        if count is not None:
            oldfile += '-v'+count
        return oldfile
    def has_image(self):
        try:
            os.stat(self.base_image())
        except:
            return False
        return True
    def get_image(self,width, height):
        oldfile = self.base_image()
        try:
            oldstat = os.stat(oldfile)
        except:
            oldfile = os.path.join(IMAGE_DIR,'user','default')
            oldstat = os.stat(oldfile)
        newfile = oldfile+('-%ix%i.jpg'%(width,height))
        try:
            newstat = os.stat(newfile)
            if newstat[stat.ST_CTIME] < oldstat[stat.ST_CTIME]:
                raise hell
        except:
            self.get_image_convert(height, width, oldfile, newfile)
        return os.path.join('user',newfile.split('/')[-1])
    def get_image_url(self, width, height):
        return '/images/'+self.get_image(width, height)
    def set_image(self, data):
        count = int(get_attr('imgupcount',self, default = '0'))
        count += 1
        set_attr('imgupcount', unicode(count), self)
        fname = os.path.join(IMAGE_DIR, 'user', unicode(self.user.id))
        fname += '-v'+unicode(count)
        destination = open(fname, 'wb+')
	for chunk in data:
        	destination.write(chunk)
    		destination.close()
        return fname
    def get_image_convert(self,height, width, oldfile, newfile):
        cmds = ['convert', '-strip', '-quality', '70']
        if (height is not None and
            width  is not None):
            cmds += ['-geometry', '%ix%i'%(width,height)]
        cmds+= [oldfile, newfile]
        os.spawnv(os.P_WAIT, '/usr/bin/convert', cmds)
    def locationbrief(self):
        s = ''
        try:
            if self.kind not in ['s','p']:
                s += get_attr('city', self)
        except:
            pass
        try:
            s2 = get_attr('province', self)
            if len(s2) > 1:
                if len(s) > 1:
                    s += ', '
                s += s2
        except:
            pass
        try:
            s2 = get_attr('country', self)
            if len(s2) > 1:
                if len(s) > 1:
                    s += ', '
                s += s2
        except:
            pass
        return s
    
    def latlng(self):
        '''
        for finding the latitude and longitude of someone, based on their location info
        '''
        l1 = self.locationbrief()
        if l1 == '':
            return None
        l0 = get_attr('latlng_locbrief',self,default=None)
        if l0 is None or l0 != l1:
            try:
                import urllib2
                q = re.sub(', ','+',l1)
                q = re.sub(' ','+',q)
                p = urllib2.build_opener().open(
                    "http://maps.google.com/maps?q=%s"%q
                    ).read()
                (lat, lng) = re.search(
                    'id:"addr",lat:(.*?),lng:(.*?),',
                    p).groups()
                set_attr('lat',lat,self)
                set_attr('lng',lng,self)
            except:
                set_attr('lat','',self)
                set_attr('lng','',self)
            set_attr('latlng_locbrief',l1,self)

        lat = get_attr('lat',self,default='')
        if lat == '':
            return None
        lng = get_attr('lng',self)
        return (float(lat),float(lng))
    
    def lat(self):
        (lat, lng) = self.latlng()
        return lat
    def lng(self):
        (lat, lng) = self.latlng()
        return lng
    
    def thumbnail(self):
        return self.get_image_url(width=THUMB_WIDTH, height=THUMB_HEIGHT)
    def has_completed_captcha(self, val=None):
        if val is not None and val == True or val == False:
            set_attr('completed_captcha', val, self)
            return val
        return get_attr('completed_captcha', self, default=False)
    def get_about(self):
        return get_attr('about', self, default='')
    def summary(self, viewer=None):
        dict = {'uname':self.user.username,
                'uid':self.user.id,
                'name':self.name,
                'picurl':self.thumbnail(),
                'picurl57':self.get_image_url(width=57, height=57),
                'location':self.locationbrief(),
                'sudoable':viewer is not None and sudoable(viewer, self.user),
                'approved':True,
                'url':self.url(),
                'edit_url':self.edit_url(),
                'summary' :stripshow(self.get_about(), maxlen=1000),
                'brief_summary': stripshow(self.get_about(), maxlen=125),
                'about' : self.get_about(),
                'kind' : self.kind,
                'isdonor' : self.kind == 'd',
                'isstudent' : self.kind == 's',
                'isproject' : self.kind == 'p',
                'isrec' : self.kind in ['s','p'],
                'isorg' : self.kind == 'o',
                'id' : self.id
                }
        vp = None
        try: vp = viewer.get_profile()
        except: pass
        vo = None
        try: vo = vp.get_object()
        except: pass
        obj = self.get_object()
        dict['obj_id'] = obj.id
        if   dict['isorg']:
            projcount = obj.recipient_set.filter(
                approved=True).filter(profile__kind='p').count()
            studcount = obj.recipient_set.filter(
                approved=True).filter(profile__kind='s').count()
            if projcount > 0:
                dict['projects'] = projcount
            if studcount > 0:
                dict['students'] = studcount
        elif dict['isrec']:
            dict['approved'] = obj.approved
            grantset = obj.grant_set.all().order_by('-created')
            curgrant = head(grantset)
            if curgrant is not None:
                if   (vp is not None and 
                      vo is not None and
                      vp.kind == 'd'):
                    cgs = curgrant.summary(vo)
                else:
                    cgs = curgrant.summary()
                dict['grant'] = cgs
                dict['grant_have'] = cgs['have']
                dict['grant_want'] = cgs['want']
            dict['grant_have_total'] = sum([g.have_informal() for g in grantset])
            dict['grant_want_total'] = sum([g.want for g in grantset])
        elif dict['isdonor']:
            dict['pledged'] = obj.pledged_informal() + obj.gift_cert_balance()
            dict['donated'] = obj.donated_informal()
        return dict
    def get_updates(self, after=None, before=None):
        obj = self.get_object()
        updates = BlogPost.objects.filter(iscomment=False).order_by('-created')
        if isinstance(obj, Donor):
            recusers = [rec.profile.user for rec in obj.get_donatees()]
            updates = updates.filter(author__in=recusers)
        if after is not None:
            updates = updates.filter(created__gt=after)
        if before is not None:
            updates = updates.filter(created__lt=before)
        return updates
    def updatecounts(self):
        #can increase cache duration if it's properly invalidated at appropriate times.
        return withcache('updatecounts|'+self.user.username,
                         _updatecounts,
                         {'prof':self}, 10*60)

def _updatecounts(d):
    prof = d['prof']
    return {
        'updates' :prof.get_updates().filter(
            created__gt=visited(
                page='account', 
                user=prof.user)).count(),
        'messages':Message.objects.filter(
            to=prof.user).filter(
            approved=True).filter(
            created__gt=visited(
                'inbox',prof.user)).count(),
        }

def updatecounts(user):
    try:
        return user.get_profile().updatecounts()
    except:
        return {'updates':0,'messages':0}

class Organization(models.Model):
    class Admin: pass
    profile = models.ForeignKey(UserProfile, unique=True)
    def __unicode__(self):
        return self.profile.user.username+u' '+self.profile.name
    def get_recipients(self):
        return Recipient.objects.filter(org=self)
    

class Recipient(models.Model):
    class Admin: pass
    profile = models.ForeignKey(UserProfile, unique=True, related_name='recipient_set')
    org = models.ForeignKey(Organization, related_name='recipient_set')
    approved = models.BooleanField()
    postneedapproval = models.BooleanField(default=True)
    def __unicode__(self):
        return self.profile.user.username+u' '+self.profile.name
    def get_donors(self):
        gs = [a for a in Grant.objects.filter(rec=self)]
        pgs = set(Paymenttogrant.objects.filter(grant__in=gs))
        donorids = set([pg.donor.id for pg in pgs
                        if not pg.isanon()])
        donors = Donor.objects.filter(id__in=donorids)
#        donors = Donor.objects.filter(
#            paymenttogrant_set__grant__in=gs).order_by(
#            '-paymenttogrant_set__grant__created')
        return donors
    def curgrant(self):
        return head(self.grant_set.all().order_by('-created'))
    def unapprove(self):
        user = self.profile.user
        profile = self.profile
        kind = self.profile.kind
        obj = self
        obj.approved = False
        obj.save()
        donors = set([])
        teams = set([])
        #go through grants
        for g in Grant.objects.filter(rec=obj):
            for pg in g.paymenttogrant_set.all():
                donors.add(pg.donor.id)
                for team in pg.donor.donorgroups.all():
                    team.numdonations -= 1
                    team.amtdonated -= pg.amount
                    team.save()
                    teams.add(team.id)
                pg.delete()
            g.update()
        donors = [Donor.objects.get(id=i).profile.user
                  for i in donors]
        donors.sort(
            lambda d1, d2: cmp(d1.username,d2.username))
        teams = [DonorGroup.objects.get(id=i)
                 for i in teams]
        for t in teams:
            t.recs.remove(obj)
            t.updatestats_deep()
        return {'donors':donors,'teams':teams}
    def receiving_messages(self):
        return get_attr('recvmsgs',self.profile,'True')=='True'

class FeaturedProfile(models.Model):
    class Admin: pass
    profile = models.ForeignKey(UserProfile)
    featuretime = models.DateTimeField(auto_now=True)


class Donor(models.Model):
    class Admin: pass
    profile = models.ForeignKey(UserProfile, unique=True)
    def receiving_messages(self):
        return True
    def __unicode__(self):
        return self.profile.user.username+u' '+self.profile.name
    def pledged_informal(self):
        return sumpw(donor=self)
    def pledged_confirmed(self):
        return sumpw(donor=self, confirmed=True)
    def have_informal(self): 
        return (sumpw(donor=self) -
                sumpg(donor=self) +
                self.gift_cert_balance())
    def have_confirmed(self):
        return (sumpw(donor=self, confirmed=True) -
                sumpg(donor=self, confirmed=True) +
                self.gift_cert_balance(confirmed=True))
    def donated_informal(self):
        return sumpg(donor=self)
    def donated_confirmed(self):
        return sumpg(donor=self, confirmed=True)
    def get_donatees(self):
        pgs = Paymenttogrant.objects.filter(donor=self)
        recs = Recipient.objects.filter(
            id__in=set([pg.grant.rec.id for pg in pgs
                        if not pg.isanon()]))
        return recs
    def gift_cert_out(self, confirmed=None):
        return sumgc(creator=self, confirmed=confirmed)
    def gift_cert_in(self, confirmed=None):
        return sumgc(receiver=self, confirmed=confirmed)
    def gift_cert_balance(self, confirmed=None):
        return (self.gift_cert_in(confirmed) -
                self.gift_cert_out(confirmed))
    def is_balance_positive(self):
        return (self.have_informal() > 0)

class DonorGroup(models.Model):
    class Admin: pass
    slug = models.SlugField(max_length=NAME_MAX, blank=True, null=True)
    name = models.CharField(max_length=NAME_MAX)
    donors = models.ManyToManyField(Donor, blank=True, null=True, related_name='donorgroups')
    admins = models.ManyToManyField(Donor, blank=True, null=True, related_name='donorgroupsadmin')
    recs   = models.ManyToManyField(Recipient, blank=True, null=True, related_name='donatinggroups')
    location = models.TextField(default='')
    category = models.TextField(default='')
    whydonate = models.TextField(default='')
    private      = models.BooleanField(default=False)
    worldjoin    = models.BooleanField(default=True)
    memberinvite = models.BooleanField(default=True)
    admininvite  = models.BooleanField(default=True)
    worldemail   = models.BooleanField(default=False)
    memberemail  = models.BooleanField(default=True)
    adminemail   = models.BooleanField(default=True)
    worldblog    = models.BooleanField(default=False)
    memberblog   = models.BooleanField(default=False)
    adminblog    = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    #statistics
    numdonors = models.IntegerField(default=0)
    amtdonated = models.IntegerField(default=0)
    numdonations = models.IntegerField(default=0)
    numstudents = models.IntegerField(default=0)
    numprojects = models.IntegerField(default=0)

    def is_cause(self):
        return self.get_cause_amt() > 0
    def get_cause_amt(self):
        return int(get_attr('cause_amount',self,'0'))
    def set_cause_amt(self,amt):
        set_attr('cause_amount',unicode(amt),self)
    def get_cause_cur(self):
        if not self.is_cause():
            return 0
        return sum([gc.amount for gc
                    in xconcat((
                        GiftCert.objects.filter(receiver=a)
                        for a in self.admins.all()))
                    if (get_attr('for_cause',gc,None)
                        == self.slug)])
#
#    int(runquery(
#            mkquery('sum(gc.amount)',
#                    ['giv_giftcert gc',
#                     'giv_attrib a',
#                     'giv_attrval av'],
#                    ["a.name='for_cause'",
#                     "a.id=av.attr_id",
#                     "av.oid=gc.id",
#                     "av.tablename='giv_giftcert'",
#                     "av.val=?"]
#                    +['(' + ' or '.join(
#                        ["gc.receiver_id=%i" % a.id
#                         for a in self.admins.all()])
#                      + ')']
#                    ),
#            [self.slug],1,1))
    
    def is_member(self, thing):
        donor = self.thing2donor(thing)
        if donor is None: return False
        return (self.donors.filter(id=donor.id).count() > 0)
    
    def join(self, donor):
        #todo: put this in a transaction...
        if not self.is_member(donor):
            self.donors.add(donor)
            self.numdonors += 1
            self.amtdonated += donor.donated_informal()
            self.numdonations += Paymenttogrant.objects.filter(donor=donor).count()
            recids = set([pg.grant.rec.id for pg in Paymenttogrant.objects.filter(donor=donor)])
            for id in recids:
                self.recs.add(Recipient.objects.get(id=id))
            self.save()
            self.updatestats()
        return
    
    def updatestats_deep(self):
        a = 0
        n = 0
        for d in self.donors.all():
            a += d.donated_informal()
            n += Paymenttogrant.objects.filter(donor=d).count()
        self.amtdonated = a
        self.numdonations = n
        self.updatestats()
        return
    
    def updatestats(self):
        self.numdonors = self.donors.count()
        self.numstudents = self.recs.filter(
            profile__kind='s').count()
        self.numprojects = self.recs.filter(
            profile__kind='p').count()
        self.save()
        return
    
    def thing2donor(self, thing):
        try:
            if isinstance(thing,Donor):
                return thing
            if isinstance(thing,User):
                thing = thing.get_profile()
            if isinstance(thing,UserProfile):
                assert thing.kind=='d'
                return thing.get_object()
        except: pass
        return None
    
    def is_admin(self, thing):
        donor = self.thing2donor(thing)
        if donor is None: return False
        return (self.admins.filter(id=donor.id).count() > 0)
    
    def add_admin(self, thing):
        donor = self.thing2donor(thing)
        self.join(donor)
        if not self.is_admin(donor):
            self.admins.add(donor)
        return
    
    def del_admin(self, thing):
        donor = self.thing2donor(thing)
        if self.is_admin(donor):
            self.admins.remove(donor)
        return
    
    def can_invite(self, thing):
        donor = self.thing2donor(thing)
        if donor is None: return False
        if self.is_admin(donor):
            return self.admininvite
        elif self.is_member(donor):
            return self.memberinvite
        return False
    
    def can_message(self, thing):
        donor = self.thing2donor(thing)
        if donor is None: return False
        if self.is_admin(donor):
            return self.adminemail
        elif self.is_member(donor):
            return self.memberemail
        return self.worldemail
    
    def can_blog(self, thing):
        donor = self.thing2donor(thing)
        if donor is None: return False
        if self.is_admin(donor):
            return self.adminblog
        elif self.is_member(donor):
            return self.memberblog
        return self.worldblog
    
    def get_image(self,width, height):
        count = get_attr('imgupcount',self, default = None)
        oldfile = os.path.join(IMAGE_DIR,'team',unicode(self.id))
        if count is not None:
            oldfile += '-v'+count
        try:
            oldstat = os.stat(oldfile)
        except:
            oldfile = os.path.join(IMAGE_DIR,'team','default')
            oldstat = os.stat(oldfile)
        newfile = oldfile+('-%ix%i.jpg'%(width,height))
        try:
            newstat = os.stat(newfile)
            assert newstat[stat.ST_CTIME] >= oldstat[stat.ST_CTIME]
        except:
            self.get_image_convert(height, width, oldfile, newfile)
        return os.path.join('team',newfile.split('/')[-1])
    def get_image_url(self, width, height):
        return '/images/'+self.get_image(width, height)
    def set_image(self, data):
        count = int(get_attr('imgupcount',self, default = '0'))
        count += 1
        set_attr('imgupcount', unicode(count), self)
        fname = os.path.join(IMAGE_DIR, 'team', unicode(self.id))
        fname += '-v'+unicode(count)
        open(fname,'wb').write(data)
        return fname
    def get_image_convert(self,height, width, oldfile, newfile):
        cmds = ['convert', '-strip', '-quality', '70']
        if (height is not None and
            width  is not None):
            cmds += ['-geometry', '%ix%i'%(width,height)]
        cmds+= [oldfile, newfile]
        os.spawnv(os.P_WAIT, '/usr/bin/convert', cmds)
    def url(self):
        return '/teams/'+self.slug+'/'
    

class Grant(models.Model):
    class Admin: pass
    rec = models.ForeignKey(Recipient, related_name='grant_set')
    want = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    have_very_informal = models.IntegerField(default=0)
    left_very_informal = models.IntegerField(default=100000)
    percent_very_informal = models.IntegerField(default=0)
    confirmed = models.BooleanField(default=False)
    def iscomplete(self):
        return (self.percent_very_informal == 100)
    def updatewithoutsave(self):
        h = self.have_informal()
        self.have_very_informal = h
        self.left_very_informal = self.want - h
        if h >= self.want:
            self.percent_very_informal = 100
        else:
            self.percent_very_informal = min(
                (h*100)/(self.want), 99)
        return self
    def update(self):
        self.updatewithoutsave().save()
        return
    def have_informal(self):
        #return sum([pg.amount for pg in self.paymenttogrant_set])
        return sumpg(grant=self)
    def have_confirmed(self):
        #return sum([pg.amount for pg in self.paymenttogrant_set.filter(confirmed=True)])
        return sumpg(grant=self, confirmed=True)
    def summary(self, don=None):
        have = self.have_informal()
        if don is None:
            donateamts = None
        else:
            dmax = min(self.want-have, don.have_informal())
            donateamts = logscale(start=5, finish=dmax)+[dmax]
            if 0 in donateamts:
                donateamts = None
        return dictcombine([
                get_attrs(self),
                {'id':self.id,
                 'want':self.want,
                 'have':have,
                 'remaining': self.want - have,
                 'percent':self.percent_very_informal,
                 'donateamts':donateamts,
                 'date':self.created,
                 }])
    def __unicode__(self):
        return u'grant, $'+unicode(self.have_very_informal)+u'/$'+unicode(self.want)+u' for '+unicode(self.rec.profile.user.username)+u' created on '+unicode(self.created)


SUBJECT_MAX_LENGTH = 200

class BlogPost(models.Model):
    '''
    a comment is just a blog post that is the child of a blog
    post. this lets us do a slashdot-style comment system if we feel
    like it, and doesnt make the typical blog comment system hard.
    each post has an author identified by username.
    '''
    class Admin: pass
    iscomment = models.BooleanField()
    author = models.ForeignKey(User)
    subject = models.CharField(max_length=SUBJECT_MAX_LENGTH)
    text = models.TextField()
    children = models.ManyToManyField("self", symmetrical=False, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    approved = models.BooleanField()
    def hastag(self,tagname):
        return self.tags.filter(tag=tagname).count() > 0
    def hastags(self,taglist):
        tgs = [t.tag for t in self.tags.all()]
        for tagname in taglist:
            if tagname in tgs: continue
            return False
        return True
    def maybesubject(self):
        s = unicode(self.subject)
        if len(s) < 1:
            return 'No Subject'
        return s
    def titleinfo(self,baseurl=None,getstr=None):
        d = {'url':self.url(baseurl=baseurl,getstr=getstr),'title':self.maybesubject()}
        d['month'] = self.created.strftime('%B %Y')
        return d
    def dicttorender(self, recurselevel=0, viewunauth=False,
                     baseurl=None,getstr=None):
        d = {}
        parents = self.blogpost_set.all()
        if self.iscomment and parents.count() > 0:
            parent = parents[0]
            d['parent'] = parent
            d['parenturl'] = parent.url()
            d['parentid'] = parent.id
        d['numcomments'] = int(self.children.all().count())
        if recurselevel != 0:
            d['children'] = [
                p.dicttorender(
                    recurselevel=recurselevel-1,
                    viewunauth=viewunauth)
                for p in 
                self.children.all().order_by('-created')
                if viewunauth or p.approved]
            if len(d['children']) == 0:
                del d['children']
        d['uname'] = unicode(self.author.username)
        d['author'] = unicode(self.author.get_profile().name)
        d['authorsummary'] = self.author.get_profile().summary()
        d['id'] = unicode(self.id)
        d['url'] = self.url(baseurl=baseurl,getstr=getstr)
        d['created'] = unicode(self.created) #todo: nicify this
        d['modified']=unicode(self.modified) #todo: nicify this
        d['subject'] = self.maybesubject()
        d['summary'] = stripshow(unicode(self.text), maxlen=1000)
        d['text'] = forshow(unicode(self.text))
        d['tags'] = [tagclean(t.tag) for t in self.tags.all()]
        d['approved'] = self.approved
        d['spamclass'] = self.getspamclass()
        d['spamtrained'] = get_attr('spamtrained',self,default=False)
        d['baseurl'] = baseurl
        d['created_day_of_month'] = ("%2i" % self.created.day).replace(' ','0')
        d['created_month_caps'] = self.created.strftime("%b").upper()
        d['created_year'] = self.created.year
        d['created_verbose_time'] = self.created.strftime("%A, %B %e, %Y at %r")
        
        # d['brief'] = d['subject'] + ' ' + stripshow(unicode(self.text), maxlen=130)
        return d
    def getspamclass(self):
        result = get_attr('spamclass',self,default=None)
        if result is not None:
            return result
        
        if self.author.is_staff:
            # staff are always hammy!
            return self.setspamclass('ham', train=True)
        
        p = self.author.get_profile()
        if p.kind in ['d','donor']:
            d = p.get_object()
            if d.pledged_informal() > 0:
                # if it's a donor who has donated, it's always ham!
                return self.setspamclass('ham', train=True)
            if len(p.get_about()) > 20 or p.has_image():
                # if it's a donor with some self-description, it's probably ham.
                return self.setspamclass('ham')
        else:
            # if it's a non-donor (eg, student or project), default to ham, but don't train.
            return self.setspamclass('ham')
        # otherwise, guess, but don't save any information.
        guess = spam.guess(unicode(self.text))
        result = {True:'spam',False:'ham'}[guess[1]>.8]
        self.setspamclass(result)
        return result
    def setspamclass(self,kind,train=False):
        if kind not in ['spam','ham']:
            raise hell
        set_attr('spamclass',kind,self)
        if train:
            prevtrained = get_attr('spamtrained',self,default=False)
            if prevtrained:
                prevkind = get_attr('spamclass',self,default=None)
                if prevkind is not None:
                    spam.untrain(prevkind,unicode(self.text))
            spam.train(kind,unicode(self.text))
            set_attr('spamtrained',True,self)
        return kind
    def url(self,baseurl=None,getstr=None):
        if getstr is None:
            getstr = ''
        else:
            getstr = '?'+getstr
        if baseurl is not None:
            return baseurl+unicode(self.id)+'/'+getstr
        return (self.author.get_profile().url() +
                'blog/' + unicode(self.id) + '/' + getstr)
    def __unicode__(self):
        return (
            unicode(self.id) + u' ' +
            unicode(self.author.username) +
            u' wrote ' +
            unicode(self.subject) +
            u' on ' +
            unicode(self.modified))


class BlogPostTag(models.Model):
    class Admin: pass
    blogpost = models.ForeignKey(BlogPost, related_name='tags')
    tag = models.CharField(max_length=TAG_MAX_LENGTH)
    def __unicode__(self):
        return (
            unicode(self.blogpost.id) +
            u' << ' +
            unicode(self.blogpost.subject) +
            u' >> ' +
            unicode(self.tag))

class Message(models.Model):
    '''
    a message from one user to another
    '''
    class Admin: pass
    fr = models.ForeignKey(User, related_name='messages_out')
    to = models.ManyToManyField(User, blank=True, null=True, related_name='messages_in')
    subject = models.CharField(max_length=SUBJECT_MAX_LENGTH)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField()
    def dicttorender(self):
        return {'from' : self.fr.username,
                'from_img' : self.from_img(),
                'to':', '.join([recvr.username 
                                for recvr 
                                in xtake(10,self.to.all())]),
                'to_img' : self.to_img(),
                'date':self.created,
                'subject' : self.subject,
                'body':forshow(self.text)}
    def from_img(self):
        return self.fr.get_profile(
            ).get_image_url(width=50,height=50)
    def to_img(self):
        tos = self.to.all()
        if tos.count()==1:
            try:
                return tos[0].get_profile(
                    ).get_image_url(width=50,height=50)
            except:
                print 'failed in to_img '+unicode(tos[0].id)
        return None
    def __unicode__(self):
        return (
            unicode(self.id) + u' ' +
            unicode(self.fr.username) +
            u' wrote ' +
            unicode(self.subject) +
            u' on ' +
            unicode(self.created))


class HideMessage(models.Model):
    '''
    messages hidden from the inbox/outbox
    '''
    class Admin: pass
    box = models.CharField(max_length=1) #'o' for outbox, 'i' for inbox
    message = models.ForeignKey(Message)
    reader = models.ForeignKey(User)
    def __unicode__(self):
        return (
            u'hide message ' +
            unicode(self.message.id) +
            u' from ' + 
            {u'o':u'out',u'i':u'in'}[self.box] + 
            u'box of ' +
            unicode(self.reader.username))


class GoogleOrder(models.Model):
    """
    this oversimplifies the google checkout schema, assuming that each
    'order' can contain only one payment to wallet. luckily we control
    the construction of shopping carts.
    """
    class Admin: pass
    identifier = models.CharField(max_length=30)
    status = models.CharField(max_length=30)
    donorid = models.IntegerField()
    amount = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    def charged(self):
        '''
        call this when notification of the donor being charged is
        received.
        '''
        try:
            pw = Paymenttowallet.objects.filter(
                kind='googlecheckout').get(
                identifier=self.identifier)
            pw.amount = self.amount
            pw.save()
        except:
            Paymenttowallet(
                donor=Donor.objects.get(id=self.donorid),
                amount=self.amount,
                kind='googlecheckout',
                identifier=self.identifier,
                ).save()
        return
    def chargebacked(self):
        '''
        call this when notification of a chargeback on this order is
        received.
        
        sends message to donor and staff that this has occured.
        
        '''
        print 'chargeback!'
        try:
            pw = Paymenttowallet.objects.filter(
                kind='googlecheckout').get(
                identifier=self.identifier)
        except:
            print 'chargeback ... but no suitable Paymenttowallet found.'
            return
        
        
        donor = pw.donor
        pw.delete()
        from proj.giv.messaging import send_message
        send_message(fr=User.objects.get(username='givbot'),
                     to=[donor.profile.user.username]+[u.username for u in User.objects.filter(is_staff=True)],
                     subject="Givology Google Checkout Error",
                     body='''
Recently, Google Checkout notified us at Givology that a payment to wallet has been cancelled, which can occur for any number of reasons. The most likely reasons include mistyped address information when signing up for Google Checkout. We will contact you soon to decide on a course of action. We apologize for any inconvenience.
'''+donor.profile.user.username+"\n\n",
                     approved=True)
        return

class Paymenttowallet(models.Model):
    class Admin: pass
    donor = models.ForeignKey(Donor, related_name='paymenttowallet_set')
    amount = models.IntegerField()
    kind = models.CharField(max_length=30) # 'googlecheckout', 'authorize.net', whatever
    identifier = models.CharField(max_length=160*2) #identifier for payment to wallet, for chargebacks or whatever
    confirmed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return u'paymenttowallet of %s of $%i via %s' % (self.donor.profile.user.username, self.amount, unicode(self.kind))


class Paymenttogrant(models.Model):
    class Admin: pass
    donor = models.ForeignKey(Donor, related_name='paymenttogrant_set')
    grant = models.ForeignKey(Grant, related_name='paymenttogrant_set')
    amount = models.IntegerField()
    confirmed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return u'paymenttogrant from %s to %s of $%i' % (self.donor.profile.user.username, self.grant.rec.profile.user.username, self.amount)
    def isanon(self):
        return (get_attr('isanon', self, 'f') == 't')

class GiftCert(models.Model):
    class Admin: pass
    creator = models.ForeignKey(Donor, related_name='gift_cert_creator_set')
    receiver = models.ForeignKey(Donor, related_name='gift_cert_receiver_set', null=True, blank=True)
    key = models.CharField(max_length=40)
    amount = models.IntegerField()
    confirmed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    received = models.DateTimeField(null=True, blank=True)
    def for_cause(self):
        return get_attr('for_cause',self,None) is not None
    def maybe_receiver_username(self):
        if self.receiver is not None:
            return self.receiver.profile.user.username
        else:
            return None
    def __unicode__(self):
        return (u'GiftCert key="%s", amount="%i"' % (self.key, self.amount) +
                u' from %s' % (self.creator.profile.user.username) +
                fif(self.receiver is not None, u' to %s' % self.maybe_receiver_username(), ''))

class GradGift(models.Model):
    class Admin: pass
    creator = models.ForeignKey(Donor, related_name='gradgift_set', null=True, blank=True)
    deliverydate = models.DateField(null=True,blank=True)
    address = models.TextField()
    schoolname = models.TextField(null=True,blank=True)
    hometown = models.TextField(null=True, blank=True)
    shoutout = models.TextField(null=True,blank=True)
    senderemail = models.TextField()
    recipientemail = models.TextField(null=True,blank=True)
    sendername = models.TextField()
    recipientname = models.TextField()
    message = models.TextField()
    #identifier of google order
    googleorder = models.CharField(null=True, blank=True, max_length=30)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class VolunteerWork(models.Model):
    class Admin: pass
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    volunteer = models.ForeignKey(User, related_name='volunteer_set')
    minutes = models.IntegerField()
    action = models.TextField()
    actionID = models.IntegerField(default=0)
    actionIsCustom = models.BooleanField(default=True)
    when = models.DateTimeField()
    def when_date_unicode(self):
        return self.when.strftime("%Y-%m-%d %H:%M:%S")




def payGrant(donor, grant, amount):
    '''
    pays a grant from a donor.
    '''
    pg = Paymenttogrant(grant=grant,
                        donor=donor,
                        amount=amount,
                        )
    iscom0 = grant.iscomplete()
    pg.save()
    grant.update()
    
    # update the 'new donations' page
    invalidatecache('donorpage_donations')
    invalidatecache('impactthisweek')
    invalidatecache('nearlydone')
    
    # update donor teams
    for team in donor.donorgroups.all():
        #todo: need to put this in a transaction...
        team.numdonations += 1
        team.amtdonated += amount
        team.recs.add(grant.rec)
        if (random.random() < (amount * 4.0 / team.amtdonated) or
            random.random() < (4.0 / team.numdonations)):
            team.updatestats_deep()
        else:
            team.updatestats()

    # if this grant just got completed, send out an email!
    if grant.iscomplete() and not iscom0:
        print "grant completed!  "+grant.rec.profile.name
        #todo: somehow make sure that people don't receive two emails for the same grant via near-simultaneous donations...
        tolist = set([pg.donor.profile.user.id
                      for pg in grant.paymenttogrant_set.all()] +
                     [a.id for a in User.objects.filter(is_staff=True)])
        tolist = [User.objects.get(id=id)
                  for id in tolist]
        
        body = tagclean(
            render_to_response(
                fif(grant.rec.profile.kind=='s',
                    'letters/completedstudent.html',
                    'letters/completedproject.html'),
                {'name':grant.rec.profile.common_name(),
                 'fullname':grant.rec.profile.name,
                 'url':grant.rec.profile.url(),
                 }).content)
        
        import proj.giv.messaging
        for u in tolist:
            proj.giv.messaging.send_message(
                User.objects.get(username='givbot'),
                [u],
                'Grant Completed!',
                body,
                approved=True)
    elif islive: # if not completed, send a thank you message
        
        htmlbody = render_to_string(
            tloc+'letters/thankyou.html',
            {'donor_url' : donor.profile.url(),
             'rec_url'   : grant.rec.profile.url(),
             'donor_name' : donor.profile.name,
             'rec_name'    : grant.rec.profile.name,
             'rec_uname'  : grant.rec.profile.user.username,
             })
        
        sendmail('giv_updates@givology.org',
                 donor.profile.user.email,
                 'Thank you for donating on Givology!',
                 body=htmlbody,
                 htmlbody=htmlbody)

    invalidatecache('nearlydone')
    invalidatecache('donorpage_donors')
    invalidatecache('donorpage_donations')
    return pg

def unpayGrant(pg):
    #todo: move the code from Recipient.unapprove here
    #warning: this function is not usable/safe
    grant = pg.grant
    pg.delete()
    grant.update()
    return


def sumpw(donor=None, confirmed=None, createdafter=None, createdbefore=None):
    if donor:
        donor = donor.id
    return tablesum(tablename=Paymenttowallet._meta.db_table,
                    donor=donor,
                    confirmed=confirmed,
                    createdafter=createdafter,
                    createdbefore=createdbefore,
                    )
def sumpg(donor=None, grant=None, confirmed=None, createdafter=None, createdbefore=None):
    if donor:
        donor = donor.id
    if grant:
        grant = grant.id
    return tablesum(tablename=Paymenttogrant._meta.db_table,
                    grant=grant,
                    donor=donor,
                    confirmed=confirmed,
                    createdafter=createdafter,
                    createdbefore=createdbefore,
                    )
def sumgc(creator=None, receiver=None, confirmed=None, createdafter=None, createdbefore=None):
    q = ('select sum(amount) from giv_giftcert '+
         'where id >= 0 ')
    if creator is not None:
        q += ' and creator_id = %i'%(creator.id)
    if receiver is not None:
        q += ' and receiver_id = %i'%(receiver.id)
    if confirmed is not None:
        if confirmed: #this is mysql specific, i think.
            q += ' and confirmed = 1'
        else:
            q += ' and confirmed = 0'
    if createdbefore is not None:
        q+=(" and created<'%s'" %
            (createdbefore.strftime("%Y-%m-%d %H:%M:%S")))
    if createdafter is not None:
        q+=(" and created>'%s'" %
            (createdafter.strftime("%Y-%m-%d %H:%M:%S")))
    cursor = connection.cursor()
    cursor.execute(q, [])
    try:
        return int(cursor.fetchall()[0][0])
    except:
        return 0

def tablesum(tablename, id=None, donor=None, grant=None, confirmed=None, createdbefore=None, createdafter=None):
    wherelist = []
    if id is not None:
        wherelist.append(' id=%i' % (id))
    if donor is not None:
        wherelist.append(' donor_id=%i' % (donor))
    if grant is not None:
        wherelist.append(' grant_id=%i' % (grant))
    if createdbefore is not None:
        wherelist.append(" created<'%s'" %
                         (createdbefore.strftime("%Y-%m-%d %H:%M:%S")))
    if createdafter is not None:
        wherelist.append(" created>'%s'" %
                         (createdafter.strftime("%Y-%m-%d %H:%M:%S")))
    if confirmed is not None:
        if confirmed: #this is mysql specific, i think.
            wherelist.append(' confirmed=1')
        else:
            wherelist.append(' confirmed=0')
    if len(wherelist)>0:
        wherestmt = 'where'+' and'.join(wherelist)
    else:
        wherestmt = ''
    query = ('select sum(amount) '+
             'from '+connection.ops.quote_name(tablename)+' '+
             wherestmt)
    cursor = connection.cursor()
    cursor.execute(query, [])
    try:
        return int(cursor.fetchall()[0][0])
    except:
        return 0
                 
class PageVisit(models.Model):
    '''statistical info on visitors'''
    class Admin: pass
    page  = models.CharField(max_length=50)
    who   = models.ForeignKey(User, blank=True, null=True)
    when  = models.DateTimeField(auto_now=True)
    ip    = models.CharField(max_length=20, blank=True, null=True)
    host  = models.TextField(blank=True, null=True)
    ref   = models.TextField(blank=True, null=True)
    agent = models.TextField(blank=True, null=True)
    def __unicode__(self):
        s = u''
        if self.ip is not None:
            s += unicode(self.ip) + u' '
        if self.host is not None:
            s += unicode(self.host) + u' '
        s += u' ' + unicode(self.when)
        return s


def logvisit(page, request):
    '''
    logs info about a person visiting a page.
    '''
    pv = PageVisit(page=page)
    who = request.user
    ip = request.META.get('REMOTE_ADDR', '')
    host = request.META.get('REMOTE_HOST', '')
    ref = request.META.get('HTTP_REFERER', '')
    agent = request.META.get('HTTP_USER_AGENT', '')
    if not isinstance(who, AnonymousUser): pv.who = who
    if ip    != '': pv.ip    = ip
    if host  != '': pv.host  = host
    if ref   != '': pv.ref   = ref
    if agent != '': pv.agent = agent
    pv.save()


class LastVisited(models.Model):
    class Admin: pass
    page = models.CharField(max_length=50)
    who  = models.ForeignKey(User)
    when = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return (unicode(self.who.username) +
                u' visited ' + 
                unicode(self.page) +
                u' on ' +
                unicode(self.when))


def visit(page, user, keep=False):
    '''
    by default we dont keep the most recent visitation, unless you set keep to True

    '''
    if not keep:
        try:
            LastVisited.objects.filter(
                page=page).filter(
                who=user).order_by(
                '-when')[0].save()
        except:
            keep = True
    if keep:
        LastVisited(page=page,
                    who=user).save()
    print page
    if page.find('inbox') < 0 or page.find('account') < 0:
        invalidatecache('updatecounts|'+user.username)
    return

def visited(page, user, default=datetime.datetime(1980,1,1)):
    '''
    '''
    try:
        return LastVisited.objects.filter(
            page=page).filter(
            who=user).order_by(
            '-when')[0].when
    except:
        return default








class Attrib(models.Model):
    class Admin: pass
    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=1, choices=KIND_CHOICES, blank=True, null=True)
    org = models.ForeignKey(Organization, related_name='attr_set', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    def __unicode__(self):
        return self.name

class AttrVal(models.Model):
    '''
    'obj' is an integer which should refer to the id of some row in some table.
    '''
    class Admin: pass
    attr = models.ForeignKey(Attrib, related_name='val_set')
    oid = models.IntegerField() #what we're applying the attribute to
    tablename = models.CharField(max_length=50) #what table it's from
    val = models.TextField()
    def __unicode__(self):
        return self.attr.name+u', '+unicode(self.oid)+u', '+self.tablename+u': '+self.val


def attrs_cachename(oid, table):
    return "attrs|" + unicode(oid) + "|" + table

def attrs_cache_f(d):
    vals = AttrVal.objects.filter(
        oid=d['oid']).filter(tablename=d['table'])
    r = {}
    r.update(
        (a,b) for (a,b)
        in ((val.attr.name,
             get_attr(val.attr.name,d['obj']))
            for val in vals)
        if a is not None and b is not None)
    return r

def get_attrs(obj):
    '''
    returns a dictionary, attribute_name:value, containing all
    attribute/value pairs involving the object passed. the object must
    be an instance of a django model, so that i can figure out its
    table.
    '''
    if obj is None:
        return {}
    oid = obj.id
    table = obj._meta.db_table
    return withcache(attrs_cachename(oid, table),
                     attrs_cache_f,
                     {'oid':oid,
                      'table':table,
                      'obj':obj,
                      })

def attr_cachename(oid, table, key):
    return "attr|" + unicode(oid) + "|" + table + "|" + key

def attr_cache_f(d):
    vals = AttrVal.objects.filter(
        oid=d['oid']).filter(
        tablename=d['table']).filter(
        attr__name=d['key'])
    if vals.count()==0:
        return 0
    else:
        return vals[0].val

def get_attr(key, obj, default='assplode'):
    '''
    like get_attrs, but returns just a value corresponding to an
    attribute name. if you want, have a default for when no value is
    found, otherwise we raise hell.
    '''
    retv = 0
    if obj is not None:
        oid = obj.id
        table = obj._meta.db_table
        retv = withcache(attr_cachename(oid, table, key),
                         attr_cache_f,
                         {'oid':oid,
                          'table':table,
                          'key':key,
                          })
    if retv != 0:
        return retv
    elif retv == 0 and default == 'assplode':
        raise hell
    elif retv == 0:
        return default

def set_attr(key, val, obj):
    '''
    sets a key/value pair corresponding to an object. if the key name
    had not existed before, its attribute table row will be created.
    '''
    oid = obj.id
    table = obj._meta.db_table
    attr = None
    try:
        attr = Attrib.objects.get(name=key)
    except:
        attr = Attrib(name=key)
        attr.save()
    av = None
    try:
        av = AttrVal.objects.filter(
            attr=attr).filter(
            oid = oid).filter(
            tablename = table)[0]
        av.val = val
    except:
        av = AttrVal(attr=attr,
                     oid = oid,
                     tablename = table,
                     val = val)
    av.save()
    invalidatecache(attrs_cachename(oid, table))
    invalidatecache(attr_cachename(oid, table, key))
    return





'''
sudo-related
'''

def sudoable(olduser, newuser):
    if isinstance(olduser, AnonymousUser):
        return False
    nprofile = newuser.get_profile()
    nobj = nprofile.get_object()
    profile = olduser.get_profile()
    obj = profile.get_object()
    if (olduser.is_staff or
        (isinstance(nobj,Recipient) and nobj.org==obj)):
        return True
    return False

def sudoid(request, newuid):
    return sudo(request, User.objects.get(id=newuid))

def sudo(request, newuser):
    try:
        newuid = newuser.id
        if not sudoable(request.user, newuser):
            raise hell
        request.session['fauxuid'] = newuid
    except:
        return False
    return True

def sudone(request):
    if 'fauxuid' in request.session:
        del request.session['fauxuid']
    return

def apparent_user(request):
    user = request.user
    user.olduser = None
    if isinstance(user, AnonymousUser):
        user.is_staff = False
        user.username = ''
    if 'fauxuid' not in request.session:
        return user
    newuid = int(request.session['fauxuid'])
    newuser = User.objects.get(id=newuid)
    if not sudoable(request.user, newuser):
        raise hell
    newuser.olduser = request.user
    return newuser

def canviewunapproved(request):
    user = apparent_user(request)
    if isinstance(user, AnonymousUser):
        return False
    return user.is_staff

def parsetags(tagstring, user=None, is_staff=None):
    tags = []
    team = None
    if user is not None and is_staff is None:
        is_staff = user.is_staff
    elif is_staff is None:
        is_staff = False
    for tag in tagstring.split(','):
        tag = tag.strip()
        tag = ''.join(
            [c for c in tag if
             c.isalnum() or c in '. -_'])
        tag = lower(tag)
        if (len(tag) > 0 and len(tag) <= TAG_MAX_LENGTH and 
            (is_staff or tag not in STAFF_TAGS or
             (tag=='notes from the field' and
              get_attr('isfellow',user,'False') == 'True'))):
            if ''.join(take(5,tag)) == 'team ':
                try:
                    team = DonorGroup.objects.get(
                        slug=''.join(drop(5,tag)))
                    if team.can_blog(user):
                        tags.append(tag)
                except: pass
            else:
                tags.append(tag)
    tags.sort()
    return tags
