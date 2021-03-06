from django.conf.urls import patterns, include, url

from django.conf import settings
from django.conf.urls.static import static

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

admin.autodiscover()

urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'the_pr.views.home', name='home'),
                       # url(r'^the_pr/', include('the_pr.foo.urls')),

                       (r'^newsletter/', include('newsletter.urls')),

                       # Uncomment the admin/doc line below to enable admin documentation:
                       url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

                       # Uncomment the next line to enable the admin:
                       url(r'^admin/', include(admin.site.urls)), ) + static(settings.MEDIA_URL,
                                                                             document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()
