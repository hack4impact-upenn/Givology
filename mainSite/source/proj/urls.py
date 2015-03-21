from django.conf.urls.defaults import *
from django.contrib import admin
import settings

handler500 = 'proj.giv.views.servererror'


urlpatterns = patterns('',
    (r'^static/(?P<path>.*)$',
     'django.views.static.serve',
     {'document_root': settings.STATIC_DIR}),
    (r'^images/(?P<path>.*)$',
     'django.views.static.serve',
     {'document_root': settings.IMAGE_DIR}),
    # (r'^admin/', include('django.contrib.admin.urls')), // COMMENTED OUT
    (r'', include('proj.giv.urls')),
)
