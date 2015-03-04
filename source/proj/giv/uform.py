


import copy
import datetime

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

from   proj.giv.htmlconv import tagclean, tagunclean, forshow
from   proj.giv.utils import *
from   proj.giv.db import *
from   proj.settings import *

from proj.giv.models import *

class UForm:
    def __init__(self, label):
        self.label = label
        self.subforms = []
        self.depth = 1
    
    def append(self, form):
        self.subforms.append(form)
        form.setdepth(self.depth+1)
    
    def setdepth(self, depth=1):
        self.depth = depth
        for form in self.subforms:
            form.setdepth(self.depth+1)
        return
    
    def renderhtml(self):
        h = 'h%i' % (self.depth)
        sf = '\n'.join(
            ['<tr><td><%s>%s</%s></td></tr>'%
             (h, self.label, h)] +
            ['<table style="padding: 10px;">'] + 
            [form.renderhtml()
             for form in self.subforms] + 
            ['</table>']
            )
        return sf
    
    def apply(self, dict):
        for form in self.subforms:
            form.apply(dict)
        return self
    
    def verify(self):
        v = True
        for form in self.subforms:
            vf = form.verify()
            if vf:
                form.error = None
            v = (v and vf)
        return v
    
    def retrieve(self):
        dict = {}
        for form in self.subforms:
            dict.update(form.retrieve())
        return dict
    
    def set_attrs(self, obj):
        for form in self.subforms:
            form.set_attrs(obj)
        return self
        
    def todefault(self):
        for form in self.subforms:
            form.todefault()
    def copy(self):
        return copy.deepcopy(self)

class InputForm(UForm):
    def __init__(self, label, key, 
                 default='', help=None, attr=None,
                 sticky=False):
        self.label = label
        self.key = key
        self.default = default
        self.value = default
        self.help = help
        self.attr = attr
        self.error = None
        self.sticky = False
        return
    
    def setdepth(self, depth=1):
        return

    def apply(self, dict):
        def ufix(s):
            from django.utils import encoding
            if isinstance(s, basestring):
                return encoding.smart_str(
                    s.replace(u'\u2019', "'").replace(u'\u201c', '"').replace(u'\u201d', '"'),
                    encoding='ascii', errors='ignore')
            else:
                return s
        if self.key in dict:
            self.value = str(ufix(dict[self.key]))
        elif self.attr and self.attr in dict:
            self.value = str(ufix(dict[self.attr]))
        return self
    
    def verify(self):
        return True
    
    def dbvalue(self):
        return tagclean(self.value)
    
    def retrieve(self):
        return {self.key : self.dbvalue()}
    
    def set_attrs(self, obj):
        if (self.attr is None):
            return
        else:
            set_attr(self.attr, self.dbvalue(), obj)
            return
    
    def todefault(self):
        if not self.sticky:
            self.value = self.default
    
    def rendererrorhtml(self):
        if (self.error is not None and
            len(self.error) > 0):
            return ''.join(
                ['\n\t\t<br />']+
                ['<span style="color: red; font-size: 80%">']+
                [self.error]+
                ['</span>'])
        return ''
    
    def renderhelphtml(self):
        if self.help is not None:
            return ''.join(
                ['\n\t\t<br />']+
                ['<span style="font-size:80%">']+
                [self.help]+
                ['</span>'])
        return ''
   
    def renderwraphtml(self, input):
        return ''.join(
            ['<tr valign="top">\n\t<td width="200px">']+
            ['\n\t\t<label for="']+[self.key]+['">']+
            [self.label]+
            ['</label>\n\t</td>\n\t<td>\n\t\t']+
            [input]+
            [self.renderhelphtml()]+
            [self.rendererrorhtml()]+
            ['\n\t</td>\n</tr>'])
            
    

class TextForm(InputForm):
    def __init__(self, label, key, 
                 default='', help=None, attr=None, 
                 sticky=False, size=30):
        InputForm.__init__(self, label, key, 
                           default, help, attr, sticky)
        self.size = str(size)
        return
    
    def renderhtml(self, inputtype='text'):
        if self.value in [None,'None']:
            self.value = ''
        return self.renderwraphtml(
            ''.join(
                ['<input type="']+
                [inputtype]+
                ['" value="']+
                [self.value]+['" name="']+
                [self.key]+['" id="']+
                [self.key]+['" size="']+
                [self.size]+['">']))

class PasswordForm(TextForm):
    def renderhtml(self):
        return TextForm.renderhtml(self, 'password')

class RequiredPasswordForm(PasswordForm):
    def verify(self):
        if self.value == self.default:
            self.error='You must enter a password!'
            return False
        return True

class IntForm(TextForm):
    def verify(self):
        if self.value == self.default:
            return True
        try:
            i = int(self.value)
        except:
            self.error='You must enter a whole number'
            return False
        return True

class RequiredIntForm(IntForm):
    def verify(self):
        if self.value == self.default:
            self.error='You must enter a value!'
            return False
        return IntForm.verify(self)

class FloatForm(TextForm):
    def verify(self):
        if self.value == self.default:
            return True
        try:
            f = float(self.value)
        except:
            self.error='You must enter a whole number'
            return False
        return True

class RequiredFloatForm(IntForm):
    def verify(self):
        if self.value == self.default:
            return False
        return FloatForm.verify(self)

class DDForm(InputForm):
    '''
    'options' is a list of pairs, fst being the value, snd being the display.
    '''
    def __init__(self, label, key,
                 default='', help=None, attr=None,
                 sticky=False, options=[('a','A')]):
        InputForm.__init__(self, label, key,
                           default, help, attr, sticky)
        self.options = []
        if not isinstance(options[0],tuple):
            for opt in options:
                self.options.append((opt,opt))
        else:
            self.options = options
        return
    
    def verify(self):
        for opt in self.options:
            if self.value == fst(opt):
                return True
        self.error='You must select one of the options!'
        return False
    
    def renderhtml(self):
        opts = ['\n\t\t\t<option value="%s"%s>%s</option>' %
                (fst(opt), 
                 {False:'',True:' selected'
                  }[fst(opt)==self.value],
                 snd(opt))
                for opt in self.options]
        return self.renderwraphtml(
            ''.join(
                ['<select class="uform-select" name="']+[self.key]+
                ['" id="']+[self.key]+['">']+
                opts+
                ['\n\t\t</select>']))    

class HiddenForm(InputForm):
    def verify(self):
        return self.default==self.value
    def renderhtml(self):
        return ('\n<input type="hidden" name="'+
                self.key+'" value="'+self.default+'">')

class RequiredTextForm(TextForm):
    def verify(self):
        v = self.value
        if v == self.default or v == '':
            self.error = 'This field is required!'
            return False
        return True

class RequiredDDForm(DDForm):
    def verify(self):
        if not DDForm.verify(self):
            return False
#        if self.value == self.default or self.value == '':
#            self.value = self.default
#            self.error = 'This choice is required!'
#            return False
        return True

def todatetime(s):
    date = None
    try:
        date = datetime.datetime.strptime(s,'%Y&ndash;%m&ndash;%d')
    except:
        date = datetime.datetime.strptime(s,'%Y-%m-%d')
    return date


class UsernameForm(TextForm):
    def verify(self):
        if not TextForm.verify(self):
            return False
        if not is_valid_username(self.value):
            self.error = 'Some characters are not allowed'
            return False
        return True

class RequiredUsernameForm(UsernameForm):
    def verify(self):
        if not UsernameForm.verify(self):
            return False
        if self.value == '':
            self.error = 'You must enter a value here!'
            return False
        return True

class DateForm(TextForm):
    def __init__(self, label, key):
        TextForm.__init__(
            self, label, key,
            'YYYY-MM-DD', size=10)
        return
    def datetime(self):
        return todatetime(self.value)
    def verify(self):
        d = None
        if self.value in [self.default, '', None, 'None']:
            return True
        try: d = self.datetime()
        except ValueError:
            self.error = 'Invalid date!<br />Note that it must be in YYYY-MM-DD format.'
            return False
        if d.year < 1901:
            self.error = 'Invalid date!<br />Year must be at least 1901.'
            return False
        return True

class RequiredDateForm(DateForm):
    def verify(self):
        if not DateForm.verify(self):
            return False
        if self.value == self.default or self.value == '':
            self.error = 'You must enter a date!'
            return False
        return True

class TextAreaForm(TextForm):
    def __init__(self, label, key, 
                 default='', help=None, attr=None, 
                 sticky=False, width=30, height=4):
        TextForm.__init__(
            self, label, key, default, help,
            attr, sticky)
        self.width = str(width)
        self.height = str(height)
    def renderhtml(self):
        return self.renderwraphtml(
            ''.join(
                ['<textarea name="']+
                [self.key]+['" id="']+
                [self.key]+['" cols="']+
                [self.width]+['" rows="']+
                [self.height]+['">']+
                [self.value]+['</textarea>']
                ))

class RequiredTextAreaForm(TextAreaForm):
    def verify(self):
        if self.value == self.default:
            self.error = 'This is required!'
            return False
        return True

def donorgroupform(request, action='Founding'):
    user = apparent_user(request)
    is_staff = user.is_staff
    if user.get_profile().kind != 'd':
        return None
    form = UForm('%s Giving Team' % action)
    if action == 'Founding':
        form.append(RequiredTextForm(
                'Team Name', 'name', ''))
    form.append(TextForm(
            'Location (optional)', 'loc', ''))
    form.append(RequiredDDForm(
            'Category (optional)', 'category',
            options=DONOR_GROUP_CATEGORIES))
    form.append(TextForm(
            'We donate because... (optional)', 'because', ''))
    form.append(TextAreaForm(
            'About (optional)', 'about', ''))
    form.append(RequiredDDForm(
            'Joining/Inviting', 'join', attr='joinprivs',
            options=['Anyone may join',
                     'Members invite people to join',
                     'Only admins can invite'],
            default='Anyone may join'))
    form.append(RequiredDDForm(
            'Messaging', 'messaging', attr='messageprivs',
            options=['Nonmembers may message the whole group',
                     'Members may message the whole group',
                     'Only admins may message the whole group'],
            default='Members may message the whole group'))
    form.append(RequiredDDForm(
            'Blogging', 'blogging',  attr='blogprivs',
            options=['Nonmembers may blog',
                     'Members may blog',
                     'Only admins may blog'],
            default='Only admins may blog'))
    form.append(IntForm(
        'Cause Amount', 'cause_amt',
        default='0'))
    
    return form.copy()


def addstudentform(request, action='Adding', grantcount=1):
    user = apparent_user(request)
    is_staff = user.is_staff
    is_org = user.get_profile().kind == 'o'
    defaultorg = '-1'
    if is_org:
        defaultorg = str(user.get_profile().get_object().id)
    form = UForm('%s a Student' % action)
    form1 = UForm('Demographic Information')
    if is_staff:
        form1.append(RequiredDDForm(
                'Partner Organization',
                'org',defaultorg,
                sticky=True,
                options=[(str(org.get_object().id), org.name)
                         for org in UserProfile.objects.filter(
                        kind='o').order_by('name')]))
    else:
        form1.append(HiddenForm(
                '','org',defaultorg))
    form1.append(RequiredTextForm(
            'Americanized Name', 'name','',))
    form1.append(TextForm(
            'Foreign Name', 'fname','',))
    form1.append(RequiredDDForm(
            'Gender', 'gender',
            options=[('a',''),('m','Male'),('f','Female')]))
    form1.append(RequiredDateForm(
            'Date of Birth', 'created'))
    form1.append(RequiredTextForm(
            'Village', 'village','',
            attr='village'))
    form1.append(RequiredTextForm(
            'Township/District', 'township', '',
            attr='township'))
    form1.append(RequiredTextForm(
            'City/County', 'city', '',
            attr='city'))
    form1.append(RequiredTextForm(
            'State/Province', 'province', '',
            attr='province'))
    form1.append(RequiredDDForm(
            'Country', 'country', '',
            options=['']+list(COUNTRIES),
            attr='country'))
    form1.append(RequiredTextAreaForm(
            'Home Address<br />(Private)', 'address','',
            'Home address; this will not be shown to any non-staff, non-partner users, but is important for INSERT REASON HERE.',
            attr='address'))
    form1.append(TextForm(
            "Father's name", 'father',
            attr='father'))
    form1.append(TextForm(
            "Mother's name", 'mother',
            attr='mother'))
    form1.append(IntForm(
            "Number of Household members (including siblings, grandparents, parents, extended family living and sharing expenses)", 'numhousehold',
            attr='numhousehold'))
    form.append(form1)
    
    form2 = UForm('Academic Information')
    form2.append(TextForm(
            'School Name', 'school_name', '',
            attr='school_name'))
    form2.append(FloatForm(
            'School Distance', 'school_distance', '',
            'Distance from home to school in km',
            attr='school_distance'))
    form2.append(RequiredDDForm(
            'Grade Type', 'edutype',
            options=[('primary','Primary School'),
                     ('middle','Middle School'),
                     ('high', 'High School'),
                     ('university', 'University')], 
            attr='edutype'))
    form2.append(RequiredDDForm(
            'Grade Level', 'edulevel',
            options=EDULEVELS, 
            attr='edulevel'))
    form2.append(TextAreaForm(
            'Extracurricular Activites', 'extra',
            attr='extra'))
    form2.append(TextAreaForm(
            'Career and Future Aspirations', 'future',
            attr='future'))
    form.append(form2)

    for i in xrange(grantcount):
        form5 = UForm('Grant Information #(%i)'%i)
        form5.append(RequiredIntForm(
            'Amount Requested', 'want_%i'%i, '',
            'Amount Requested for grant in USD',
            size=3))
        form5.append(TextForm(
            'F-ING BRIEF description (like, 10 letters max)', 'grant_annotation_%i'%i,
            attr='grant_annotation',
            size=10))
        form5.append(RequiredIntForm(
            'Tuition', 'cost_tuition_%i'%i,
            attr='cost_tuition',
            size=2))
        form5.append(RequiredIntForm(
            'School Supplies', 'cost_supplies_%i'%i,
            attr='cost_supplies',
            size=2))
        form5.append(RequiredIntForm(
            'Textbooks', 'cost_textbooks_%i'%i,
            attr='cost_textbooks',
            size=2))
        form5.append(RequiredIntForm(
            'Transportation', 'cost_transport_%i'%i,
            attr='cost_transport',
            size=2))
        form5.append(RequiredIntForm(
            'Room and Board', 'cost_roomnboard_%i'%i,
            attr='cost_roomnboard',
            size=2))
        form5.append(RequiredIntForm(
            'Other', 'cost_other_%i'%i,
            attr='cost_other',
            help='there is no check that these add up yet.',
            size=2))
        form.append(form5)


    form3 = UForm('Student Biography')
    form3.append(RequiredTextAreaForm(
            '', 'about', '',
            attr='about',
            ))

    form.append(form3)

    form4 = UForm('Financial Information')
    form4.append(IntForm(
            'Estimated Annual Family Income (US$)',
            'annual_income', '', attr='annual_income'))
    form4.append(DDForm(
            'Occupation of father', 'occ_father',
            options=[(x, x) for x in (['']+[a for a in FATHER_OCCS])],
            attr='occ_father',
            ))
    form4.append(DDForm(
            'Occupation of mother', 'occ_mother',
            options=[(x, x) for x in (['']+[a for a in MOTHER_OCCS])],
            attr='occ_mother',
            ))
    form.append(form4)
    

    form6 = UForm('Administrative Information')
    form6.append(TextForm(
            'School Contact Name',
            'school_contact', '', attr='school_contact'))
    form6.append(TextForm(
            'School Contact Phone Number',
            'school_contact_phone', '', attr='school_contact_phone'))
    form6.append(RequiredDDForm(
            'Receiving Messages', 'recvmsgs', attr='recvmsgs',
            options=[('True','Yes'),('False','No')]))
    form.append(form6)

    
    
    return form.copy()



def addprojectform(request, action='Adding', grantcount=1):
    '''
    '''
    user = apparent_user(request)
    is_staff = user.is_staff
    is_org = user.get_profile().kind == 'o'
    defaultorg = '-1'
    if is_org:
        defaultorg = str(user.get_profile().get_object().id)
    form = UForm('%s a Project' % action)
    form1 = UForm('Demographic Information')
    if is_staff:
        form1.append(RequiredDDForm(
                'Partner Organization',
                'org',defaultorg,
                sticky=True,
                options=[(str(org.get_object().id), org.name)
                         for org in UserProfile.objects.filter(
                        kind='o').order_by('name')]))
    else:
        form1.append(HiddenForm(
                '','org',defaultorg))
    
    form1.append(RequiredTextForm(
            'Americanized Name', 'name','',))
    form1.append(TextForm(
            'Foreign Name', 'fname','',))
    form1.append(TextForm(
            'Project Purpose', 'purpose',attr='proj_purpose',))
    form1.append(RequiredDDForm(
            'Project Type', 'type',
            options=[
                ('School Refurbishment','School Refurbishment'),
                ('Textbooks and Supplies','Textbooks and Supplies'),
                ('Technology Upgrade','Technology Upgrade'),
                ('School Construction','School Construction'),
                ('Training and Development','Training and Development'),
                ('Other','Other'),], 
            attr='proj_type'))
    form1.append(IntForm('Number of Students Helped', 'numhelped', attr='numhelped'))
    form1.append(DDForm(
            'Type of Students Served', 'edutype',
            options=['Primary School',
                     'Middle School',
                     'High School',
                     'University'],
            attr='edutype'))
    form1.append(TextForm(
            'Name of Affiliated School',
            'school_name', '', attr='school_name'))
    form1.append(RequiredTextForm(
            'Village', 'village','',
            attr='village'))
    form1.append(RequiredTextForm(
            'Township/District', 'township', '',
            attr='township'))
    form1.append(RequiredTextForm(
            'City/County', 'city', '',
            attr='city'))
    form1.append(RequiredTextForm(
            'State/Province', 'province', '',
            attr='province'))
    form1.append(RequiredDDForm(
            'Country', 'country', '',
            options=['']+list(COUNTRIES),
            attr='country'))
    
    form.append(form1)

    for i in xrange(grantcount):
        form5 = UForm('Grant Information #(%i)'%i)
        form5.append(RequiredIntForm(
            'Amount Requested', 'want_%i'%i, '',
            'Amount Requested for grant in USD',
            size=3))
        form5.append(TextForm(
            'F-ING BRIEF description (like, 10 letters max)', 'grant_annotation_%i'%i,
            attr='grant_annotation',
            size=10))
        form5.append(RequiredIntForm(
            'Supplies and Furniture', 'cost_supplies_%i'%i,
            attr='cost_supplies',
            size=2))
        form5.append(RequiredIntForm(
            'Labor Costs and Salaries', 'cost_labor_%i'%i,
            attr='cost_labor',
            size=2))
        form5.append(RequiredIntForm(
            'Transportation', 'cost_transport_%i'%i,
            attr='cost_transport',
            size=2))
        form5.append(RequiredIntForm(
            'Raw Materials', 'cost_materials_%i'%i,
            attr='cost_materials',
            size=2))
        form5.append(RequiredIntForm(
            'Research and Development', 'cost_rnd_%i'%i,
            attr='cost_rnd',
            size=2))
        form5.append(RequiredIntForm(
            'Administrative Expenses', 'cost_admin_%i'%i,
            attr='cost_admin',
            size=2))
        form5.append(RequiredIntForm(
            'Other', 'cost_other_%i'%i,
            attr='cost_other',
            help='there is no check that these add up yet.',
            size=2))
        form.append(form5)
    
    form2 = UForm('Project Profile')
    form2.append(RequiredTextAreaForm(
            'Project Description',
            'about',
            attr='about'))
    form2.append(TextAreaForm(
            'Project History',
            'history',
            attr='history'))
    form2.append(TextAreaForm(
            'Project Impact',
            'impact',
            attr='impact'))
    form2.append(TextAreaForm(
            'Project Team Credentials',
            'team_credentials',
            attr='team_credentials'))
    
    form.append(form2)
    
    form3 = UForm('Project Contact Details')
    form3.append(TextForm(
            'Project Leader Name',
            'proj_lead_name',
            attr='proj_lead_name'))
    form3.append(TextForm(
            'Project Leader Name (Foreign)',
            'proj_lead_fname',
            attr='proj_lead_fname'))
    form3.append(TextForm(
            'Phone Number',
            'proj_contact_phone',
            attr='proj_contact_phone'))
    form3.append(TextForm(
            'Email',
            'proj_contact_email',
            attr='proj_contact_email'))
    form3.append(TextAreaForm(
            'Address',
            'proj_contact_address',
            attr='proj_contact_address'))
    form3.append(RequiredDDForm(
            'Receiving Messages', 'recvmsgs', attr='recvmsgs',
            options=[('True','Yes'),('False','No')]))
    form.append(form3)
    
    return form.copy()











def newdonorform(request):
    form = UForm('Creating a Donor Account')
    form.append(RequiredTextForm(
            'Name', 'name', ''))
    form.append(RequiredTextForm(
            'Email Address', 'email', '', help='Your email address will NOT be displayed on the site, but is very important for the site to function (eg, receive payments from you).'))
    form.append(RequiredUsernameForm(
            'New Username', 'username', ''))
    form.append(RequiredPasswordForm(
            'New Password', 'password', ''))
    form.append(TextForm(
            'How did you hear about Givology? (optional)', 'heard', '',
            attr='heard',
            ))
    return form.copy()
    
def editdonorform(request):
    form = UForm('Editing Donor Information')
    form.append(RequiredTextForm(
            'Name', 'name', ''))
    form.append(RequiredTextForm(
            'Email Address', 'email', '', help='Your email address will NOT be displayed on the site, but is very important for the site to function (eg, receive payments from you).'))
    form.append(DDForm(
            'Gender', 'gender',
            options=[('a',''),('m','Male'),('f','Female')]))
    form.append(DateForm(
            'Date of Birth', 'created'))
    form.append(TextForm(
            'City/County', 'city', '',
            attr='city'))
    form.append(TextForm(
            'State/Province', 'province', '',
            attr='province'))
    form.append(TextForm(
            'Country', 'country', '',
            attr='country'))
    form.append(DDForm(
            'Anonymity', 'isanon',
            options=[('f','Public'),('t', 'Private')],
            attr='isanon'))
    form.append(TextAreaForm(
            'About / Interests', 'about', '',
            attr='about',
            ))
    form.append(DDForm(
            'Student?', 'donor_student',
            options=[('a',''),('y','Yes'),('n','No')],
            attr='donor_student',
            ))
    form.append(TextForm(
            'Name of School (if student)', 
            'donor_school', 
            '', 
            attr='donor_school'))
    form.append(DDForm(
            'Job Type / Industry', 'industry',
#            options=[(x,x) for x in industries],
            options=[(str(i),industries[i]) 
                     for i in xrange(len(industries))],
            attr='industry',
            ))
    form.append(TextForm(
            'Company Name', 
            'company', 
            '', 
            attr='company'))
    form.append(TextForm(
            'Title in Company', 
            'company_title', 
            '', 
            attr='company_title'))
    return form.copy()


PARTNER_STATES = [
    'In Progress',
    'Partner',
    'Cancelled',
    ]



def addorganizationform(request, action='Adding'):
    '''
    '''
    user = apparent_user(request)
    is_staff = user.is_staff
    assert is_staff
    
    form = UForm('%s a Partner' % action)
    form1 = UForm('Basic Information')
    form2 = UForm('Profile')
    
    form1.append(RequiredDDForm(
            'Partnership Status', 'pstatus', '',
            options=PARTNER_STATES,
            attr='pstatus'))
    form1.append(RequiredTextForm('Partner Name','name',''))
    form1.append(TextForm('Website URL','purl','',attr='url'))
    form1.append(RequiredTextForm(
            'City of Headquarters','city','',attr='city'))
    form1.append(RequiredTextForm(
            'Country of Headquarters',
            'country','',attr='country'))
    form1.append(RequiredDateForm(
            'Date of Founding', 'created'))
    form1.append(RequiredTextForm(
            'Countries of Operation','opcountries','',
            'List countries separated by commas.',
            attr='opcountries'))
    
    form2.append(RequiredTextAreaForm(
            'Description','description','',attr='description'))
    form2.append(RequiredTextAreaForm(
            'Impact','impact','',attr='impact'))
    form2.append(RequiredTextAreaForm(
            'Interactions with Givology',
            'interactions','',attr='interactions'))
    
    form.append(form1)
    form.append(form2)
    
    return copy.deepcopy(form)
    
    



















industrytxt = '''
Accounting
Airlines/Aviation
Alternative Dispute Resolution
Alternative Medicine
Animation
Apparel &amp; Fashion
Architecture &amp; Planning
Arts and Crafts
Automotive
Aviation &amp; Aerospace
Banking
Biotechnology
Broadcast Media
Building Materials
Business Supplies and Equipment
Capital Markets
Chemicals
Civic &amp; Social Organization
Civil Engineering
Commercial Real Estate
Computer &amp; Network Security
Computer Games
Computer Hardware
Computer Networking
Computer Software
Construction
Consumer Electronics
Consumer Goods
Consumer Services
Cosmetics
Dairy
Defense &amp; Space
Design
Education Management
E-Learning
Electrical/Electronic Manufacturing
Entertainment
Environmental Services
Events Services
Executive Office
Facilities Services
Farming
Financial Services
Fine Art
Fishery
Food &amp; Beverages
Food Production
Fund-Raising
Furniture
Gambling &amp; Casinos
Glass, Ceramics &amp; Concrete
Government Administration
Government Relations
Graphic Design
Health, Wellness and Fitness
Higher Education
Hospital &amp; Health Care
Hospitality
Human Resources
Import and Export
Individual &amp; Family Services
Industrial Automation
Information Services
Information Technology and Services
Insurance
International Affairs
International Trade and Development
Internet
Investment Banking
Investment Management
Judiciary
Law Enforcement
Law Practice
Legal Services
Legislative Office
Leisure, Travel &amp; Tourism
Libraries
Logistics and Supply Chain
Luxury Goods &amp; Jewelry
Machinery
Management Consulting
Maritime
Marketing and Advertising
Market Research
Mechanical or Industrial Engineering
Media Production
Medical Devices
Medical Practice
Mental Health Care
Military
Mining &amp; Metals
Motion Pictures and Film
Museums and Institutions
Music
Nanotechnology
Newspapers
Non-Profit Organization Management
Oil &amp; Energy
Online Media
Outsourcing/Offshoring
Package/Freight Delivery
Packaging and Containers
Paper &amp; Forest Products
Performing Arts
Pharmaceuticals
Philanthropy
Photography
Plastics
Political Organization
Primary/Secondary Education
Printing
Professional Training &amp; Coaching
Program Development
Public Policy
Public Relations and Communications
Public Safety
Publishing
Railroad Manufacture
Ranching
Real Estate
Recreational Facilities and Services
Religious Institutions
Renewables &amp; Environment
Research
Restaurants
Retail
Security and Investigations
Semiconductors
Shipbuilding
Sporting Goods
Sports
Staffing and Recruiting
Supermarkets
Telecommunications
Textiles
Think Tanks
Tobacco
Translation and Localization
Transportation/Trucking/Railroad
Utilities
Venture Capital &amp; Private Equity
Veterinary
Warehousing
Wholesale
Wine and Spirits
Wireless
Writing and Editing'''
industries = industrytxt.split('\n')
industries.sort()
