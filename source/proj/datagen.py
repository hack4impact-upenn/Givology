"""
Script to generate students and orgs which they belong to

To add 10 students:
% python manage.py shell
> import datagen
> datagen.add(10)

To add 10 more students:
> datagen.add(10, first=10)
"""

from giv.models import *

def add(N, id='student', first=0):
    for i in range(first, first+N):
        uname = id + str(i)
        print ('creating %s...' % uname),
        u = User.objects.create_user(username=uname, email='', password='pw' )
        u.save()
        p = UserProfile(user=u, 
                        kind=id[0], 
                        name=uname, 
                        created=datetime.date.today(),
                        about="I'm an automatically generated student.",
                        locality='cyberspace',
                        country='USA',
                        postal_code='10101',
                        )
        p.save()
        if (Organization.objects.all().count() < 1):
            o = makeorg()
        r = Recipient(profile=p, 
                      org=Organization.objects.all()[0],
                      approved=True,

                      )
        r.save()
        print 'done'
def makeorg(n=0):
    uname = 'org'+str(n)
    print ('creating %s...' % uname),
    u = User.objects.create_user(username=uname, email='', password='pw' )
    u.save()
    p = UserProfile(user=u, kind='o', name=uname, created=datetime.date.today())
    p.save()
    o = Organization(profile=p)
    o.save()
    return o
