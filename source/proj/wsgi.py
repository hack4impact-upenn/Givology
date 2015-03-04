#!/user/bin/python

import newrelic.agent
newrelic.agent.initialize('/opt/givologyProd/mainSite/source/proj/newrelic.ini')

import sys, os

sys.path.append('/opt/givologyProd/mainSite/source/proj')
sys.path.append('/opt/givologyProd/mainSite/source')
os.environ['DJANGO_SETTINGS_MODULE'] = 'proj.settings'


import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
