from django.conf.urls import patterns, include, url
import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()
urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'demo_bank.views.home', name='home'),
    # url(r'^demo_bank/', include('demo_bank.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
	url(r'^accounts/profile/', RedirectView.as_view(url='/admin/')),
    url(r'^admin/', include(admin.site.urls)),	
	url(r'^media/(?P<path>.*)$', "django.views.static.serve", {'document_root':"../demo_bank/site_media"})                                   
)

urlpatterns += staticfiles_urlpatterns()
