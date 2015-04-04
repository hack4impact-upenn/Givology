from django.conf.urls.defaults import *

urlpatterns = patterns(
    'proj.giv.views',
    (r'^comingsoon/$', 'comingsoon'),
    (r'^robots.txt$', 'robotstxt'),
    (r'^favicon.ico$', 'faviconredir'),


    # HACK4IMPACT TEMP URLS - TO DELETE
    (r'^impact/$', 'impact'), 
    (r'^similar/$', 'similar'), 
    (r'^blog/$', 'blog'), 



    #(r'^nyc/$', 'nyc'),                             #marquis promotion (2009)

    (r'^$', 'index'),                                #frontpage
    (r'^rss/(?P<tags>[, \w]+)/$', 'givrss'),         #rss (fixed?)               SLOW
    (r'^socialactionsfeed/$', 'socialactionsfeed'),  #socialactionsfeed (fixed?) SLOW
                       
    (r'^who-we-are/$', 'whoweare'),
    (r'^who-we-are/how-it-works/$', 'howitworks'),
    (r'^who-we-are/mission-vision/$', 'missionvision'),
    (r'^who-we-are/board-of-directors/$', 'boardofdirectors'),    # SLOW (why?)
    (r'^who-we-are/executive-team/$', 'executiveteam'),           # needs updating!
    (r'^who-we-are/partnerships/$', 'partnerships'),
    (r'^who-we-are/faq/$', 'faq'),
    (r'^who-we-are/contact-us/$', 'contactus'),
    (r'^our-community/$', 'ourcommunity'),
    (r'^our-community/our-donors/$', 'ourdonors'),                # SLOW !!!
    (r'^our-community/field-partners/$', 'fieldpartners'),        # kinda slow
    (r'^our-community/giving-teams/$', 'givingteams'),
    (r'^giv-now/$', 'givnow'),
    (r'^giv-now/giv-students/$', 'givstudents'),
    (r'^giv-now/giv-projects/$', 'givprojects'),
    (r'^giv-now/giv-givology/$', 'givgivology'),
    (r'^giv-now/gift-certificates/$', 'giftcertificates'),
    (r'^giv-now/gift-certificates/accept/$', 'accept_gift_card'),
    (r'^get-involved/$', 'getinvolved'),
    (r'^get-involved/start-chapter/$', 'startchapter'),
    (r'^get-involved/volunteer/$', 'volunteer'),
    (r'^get-involved/internships/$', 'internships'),
    (r'^get-involved/fellowships/$', 'fellowships'),
    (r'^get-involved/spread-the-word/$', 'spreadtheword'),
    (r'^(?P<base_url>blogs/)$', 'blogs'),
    (r'^(?P<base_url>blogs/)tag/(?P<selected_encoded_tag>[^/]+)/$', 'blogs'),
    (r'^(?P<base_url>blogs/notes-from-the-field/)$', 'field_blogs'),
    (r'^(?P<base_url>blogs/notes-from-the-field/)tag/(?P<selected_encoded_tag>[^/]+)/$', 'field_blogs'),
    (r'^(?P<base_url>blogs/students/)$', 'student_blogs'),
    (r'^(?P<base_url>blogs/students/)tag/(?P<selected_encoded_tag>[^/]+)/$', 'student_blogs'),
    (r'^(?P<base_url>blogs/projects/)$', 'project_blogs'),
    (r'^(?P<base_url>blogs/projects/)tag/(?P<selected_encoded_tag>[^/]+)/$', 'project_blogs'),
    (r'^giv-media/$', 'media'),    #OK
    (r'^giv-media/photos/$', 'photos'),
    (r'^giv-media/videos/$', 'videos'),
    (r'^giv-media/press/$', 'press'),
    (r'^giv-media/annual-reports/$', 'annualreports'),
    (r'^shop/$', 'shop'),          #OK

                       
    (r'^register/$', 'newdonor'),
    (r'^newpassword/$', 'newpassword'),
    (r'^about/$', 'whoweare'),
    (r'^invite-friends-action/$','invite_friends_action'),


    (r'^vision/$', 'vision'),
    (r'^FAQ/$', 'faq'),
    (r'^team/$', 'team'),                      #broken
    (r'^team/(?P<name>\w+)/$', 'teamspecific'),
    (r'^contact/$', 'contactus'),
    (r'^policy/$', 'policy'),
    (r'^terms/$', 'terms'),
	

    (r'^donors/$', 'donors'),                     #a little slow and really uggo
    (r'^donorsearch/$', 'donorsearch'),
    (r'^partners/$', 'organizationsearch'),        #broken? replaced by our-community/field-partners?
    (r'^teams/$', 'teams'),                        #really uggo
    (r'^teams/create/$', 'team_create'),
    (r'^teams/(?P<slug>[-_\w]+)/$', 'teamview'),                  #is this used???
    (r'^teams/(?P<slug>[-_\w]+)/edit/$', 'team_edit'),
    (r'^teams/(?P<slug>[-_\w]+)/join/$', 'team_join'),
    (r'^teams/(?P<slug>[-_\w]+)/invite/$', 'team_invite'),
    (r'^teams/(?P<slug>[-_\w]+)/blog/$', 'team_blog'),
    (r'^teams/(?P<slug>[-_\w]+)/message/$', 'team_message'),
    (r'^teams/(?P<slug>[-_\w]+)/img/$', 'teamviewimg'),
    (r'^teams/(?P<slug>[-_\w]+)/addadmin/$', 'team_addadmin'),
    (r'^teams/(?P<slug>[-_\w]+)/givecause/$', 'givecause'),
    (r'^multimedia/$', 'multimedia'),                             #deprecated??
    (r'^getinvolved_about/$', 'getinv_about'),                    #deprecated??
    (r'^community_about/$', 'comm_about'),                        #deprecated??

    (r'^donate/$', 'donate'),
    (r'^donate/students/$', 'donatestudents'),
    (r'^donate/projects/$', 'donateprojects'),
    (r'^donate/ffstudents/$', 'donateffstudents'),
    (r'^donate/ffprojects/$', 'donateffprojects'),
    (r'^sponsorships/$', 'sponsorships'),
    (r'^giftcert/$', 'giftcertificates'),
    (r'^gradgift/$', 'gradgift'),
    (r'^merchandise/$', 'merchandise'),

    (r'^news/$', 'blogs'),                       #duplicate links(4)
    (r'^studentupdates/$', 'student_blogs'),
    (r'^projectupdates/$', 'project_blogs'),
    (r'^notesfromthefield/$', 'field_blogs'),

    (r'^startachapter/$', 'startachapter'),      #duplicate links
    (r'^volunteer/$', 'volunteer'),
    (r'^internships/$', 'internships'),
    (r'^fellowships/$', 'fellowships'),
    (r'^partnerships/$', 'partnerships'),
    (r'^gdonate/$', 'getinvolveddonate'),

    (r'^volunteered/$', 'volunteered'),
    (r'^account/$', 'account'),
    (r'^autodonate/$', 'autodonate'),
    (r'^account/confirm/$', 'confirmnewdonor'),
    (r'^account/rss.xml$', 'accountrss'),
    (r'^addstudent/$', 'addstudent'),
    (r'^addproject/$', 'addproject'),
    (r'^addorganization/$', 'addorganization'),
    (r'^wallet/$', 'wallet'),
    (r'^walletadd/$', 'walletadd'),
    (r'^walletadded/$', 'walletadded'),

    (r'^compose/$', 'compose'),
    (r'^preview/$', 'preview'),
    (r'^preview/json/$', 'previewjson'),
    (r'^composed/$', 'composed'),
    (r'^deleteblogpost/(?P<post_id>\d+)/$', 'deleteblogpost'),
    (r'^donated/$', 'donated'),
    (r'^composeimg/$', 'composeimg'),

    (r'^~(?P<uname>\w+)/$', 'pubview'),
    (r'^~(?P<uname>\w+)/editprofile/$', 'editprofile'),
    (r'^~(?P<uname>\w+)/editprofilemini/$', 'editprofilemini'),
    (r'^~(?P<uname>\w+)/map_(?P<width>\w+)_(?P<height>\w+).jpg$', 'pubviewmap'),
    (r'^~(?P<uname>\w+)/img/$', 'pubviewimg'),
    (r'^(?P<base_url>~(?P<uname>\w+)/blog/)$', 'blogs'),
    (r'^(?P<base_url>~(?P<uname>\w+)/blog/)tag/(?P<selected_encoded_tag>[^/]+)/$', 'blogs'),
    (r'^~(?P<uname>\w+)/blog/(?P<entry_id>\d+)/$', 'userblogview'),
    (r'^~(?P<uname>\w+)/blog/archive/$', 'blogarchiveview'),
    (r'^~(?P<uname>\w+)/blog/rss.xml$', 'blogrss'),
    (r'^~(?P<uname>\w+)/outbox/$', 'outbox'),
    (r'^~(?P<uname>\w+)/inbox/$', 'inbox'),
    (r'^~(?P<uname>\w+)/outbox/(?P<message_id>\d+)/$', 'message_out'),
    (r'^~(?P<uname>\w+)/inbox/(?P<message_id>\d+)/$', 'message_in'),
    (r'^~(?P<uname>\w+)/addgrant/$', 'addgrant'),

    (r'^login/$', 'login_view'),
    (r'^logout/$', 'logout_view'),
    (r'^admin/approve/$', 'approve'),
    (r'^approvepost/$', 'approvepost'),
    (r'^markblogham/$', 'markblogham'),
    (r'^markblogspam/$', 'markblogspam'),
    (r'^markfellow/$','markfellow'),
    (r'^gcheckout/$', 'gcheckoutnotification'),
    (r'^givstyle.css$', 'givstyle'),
    (r'^givstyles.css$', 'givstyles'),

    (r'^partnerstats/$', 'partnerstats'),
    (r'^recipientstats/$', 'recipientstats'),
    (r'^donorstats/$', 'donorstats'),
    (r'^donors.csv$', 'donorcsv'),
    (r'^recipients.csv$', 'recipcsv'),
    (r'^donormessages/$', 'donormessages'),
    (r'^donations.csv$', 'donationcsv'),
    (r'^payments.csv$', 'paymentcsv'),
    (r'^giftcerts.csv$', 'giftcertcsv'),
    (r'^adddonor/$', 'adddonor'),

    (r'^error/$', 'errorpage'),
    (r'^cache/$', 'memcachedpage'),

    (r'^(?P<url0>.*)(?P<url1>[^/]+)$', 'slashredir'),
    
)



