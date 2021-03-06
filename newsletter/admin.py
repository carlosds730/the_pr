import logging

logger = logging.getLogger(__name__)

import sorl.thumbnail

from django.db import models

import models as md

from django.conf.urls import patterns, url

from django.contrib import admin, messages
from django.contrib.sites.models import Site

from django.core import serializers

from django.http import HttpResponse, HttpResponseRedirect

from django.template import RequestContext, Context

from django.shortcuts import render_to_response

from django.utils.translation import ungettext, ugettext_lazy as _
from django.utils.formats import date_format

from django.views.decorators.clickjacking import xframe_options_sameorigin

from sorl.thumbnail.admin import AdminImageMixin

from .models import (
    Article, Message, Publicity
)
from wrapper import WrapperRSS

from django.utils.timezone import now

from .admin_forms import *
from .admin_utils import *

from .settings import newsletter_settings

# Contsruct URL's for icons
ICON_URLS = {
    'yes': '%sadmin/img/icon-yes.gif' % settings.STATIC_URL,
    'wait': '%snewsletter/admin/img/waiting.gif' % settings.STATIC_URL,
    'submit': '%snewsletter/admin/img/submitting.gif' % settings.STATIC_URL,
    'no': '%sadmin/img/icon-no.gif' % settings.STATIC_URL
}


class NewsletterAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'admin_subscriptions', 'admin_messages', 'admin_submissions'
    )
    prepopulated_fields = {'slug': ('title',)}

    """ List extensions """

    def admin_messages(self, obj):
        return '<a href="../message/?newsletter__id__exact=%s">%s</a>' % (
            obj.id, ugettext('Messages')
        )

    admin_messages.allow_tags = True
    admin_messages.short_description = ''

    def admin_subscriptions(self, obj):
        return \
            '<a href="../subscription/?newsletter__id__exact=%s">%s</a>' % \
            (obj.id, ugettext('Subscriptions'))

    admin_subscriptions.allow_tags = True
    admin_subscriptions.short_description = ''

    def admin_submissions(self, obj):
        return '<a href="../submission/?newsletter__id__exact=%s">%s</a>' % (
            obj.id, ugettext('Submissions')
        )

    admin_submissions.allow_tags = True
    admin_submissions.short_description = ''


class SubmissionAdmin(admin.ModelAdmin, ExtendibleModelAdminMixin):
    form = SubmissionAdminForm
    list_display = (
        'admin_message', 'admin_newsletter', 'admin_publish_date', 'publish',
        'admin_status_text', 'admin_status'
    )
    date_hierarchy = 'publish_date'
    list_filter = ('newsletter', 'publish', 'sent')
    save_as = True
    filter_horizontal = ('subscriptions',)

    """ List extensions """

    def admin_message(self, obj):
        return '<a href="%d/">%s</a>' % (obj.id, obj.message.title)

    admin_message.short_description = ugettext('submission')
    admin_message.allow_tags = True

    def admin_newsletter(self, obj):
        return '<a href="../newsletter/%s/">%s</a>' % (
            obj.newsletter.id, obj.newsletter
        )

    admin_newsletter.short_description = ugettext('newsletter')
    admin_newsletter.allow_tags = True

    def admin_publish_date(self, obj):
        if obj.publish_date:
            return date_format(obj.publish_date)
        else:
            return ''

    admin_publish_date.short_description = _("publish date")

    def admin_status(self, obj):
        if obj.prepared:
            if obj.sent:
                return u'<img src="%s" width="10" height="10" alt="%s"/>' % (
                    ICON_URLS['yes'], self.admin_status_text(obj))
            else:
                if obj.publish_date > now():
                    return \
                        u'<img src="%s" width="10" height="10" alt="%s"/>' % (
                            ICON_URLS['wait'], self.admin_status_text(obj))
                else:
                    return \
                        u'<img src="%s" width="12" height="12" alt="%s"/>' % (
                            ICON_URLS['wait'], self.admin_status_text(obj))
        else:
            return u'<img src="%s" width="10" height="10" alt="%s"/>' % (
                ICON_URLS['no'], self.admin_status_text(obj))

    admin_status.short_description = ''
    admin_status.allow_tags = True

    def admin_status_text(self, obj):
        if obj.prepared:
            if obj.sent:
                return ugettext("Sent.")
            else:
                if obj.publish_date > now():
                    return ugettext("Delayed submission.")
                else:
                    return ugettext("Submitting.")
        else:
            return ugettext("Not sent.")

    admin_status_text.short_description = ugettext('Status')

    """ Views """

    def submit(self, request, object_id):
        submission = self._getobj(request, object_id)

        if submission.sent or submission.prepared:
            messages.info(request, ugettext("Submission already sent."))
            return HttpResponseRedirect('../')

        submission.prepared = True
        submission.save()
        adm_msg = submission.submit()

        if adm_msg[1] == 1:
            messages.info(request, ugettext(adm_msg[0]))
        else:
            messages.error(request, ugettext(adm_msg[0]))

        return HttpResponseRedirect('../../')

    """ URLs """

    def get_urls(self):
        urls = super(SubmissionAdmin, self).get_urls()

        my_urls = patterns(
            '', url(
                r'^(.+)/submit/$',
                self._wrap(self.submit),
                name=self._view_name('submit')
            )
        )

        return my_urls + urls


StackedInline = admin.StackedInline
if (
            newsletter_settings.RICHTEXT_WIDGET
        and newsletter_settings.RICHTEXT_WIDGET.__name__ == "ImperaviWidget"
):
    # Imperavi works a little differently
    # It's not just a field, it's also a media class and a method.
    # To avoid complications, we reuse ImperaviStackedInlineAdmin
    try:
        from imperavi.admin import ImperaviStackedInlineAdmin

        StackedInline = ImperaviStackedInlineAdmin
    except ImportError:
        # Log a warning when import fails as to aid debugging.
        logger.warning(
            'Error importing ImperaviStackedInlineAdmin. '
            'Imperavi WYSIWYG text editor might not work.'
        )


class ArticleInline(AdminImageMixin, StackedInline):
    model = Article
    extra = 1
    fieldsets = (
        (None, {
            'fields': ('title', 'sortorder', 'text', 'url', 'image')
        }),
    )

    if newsletter_settings.RICHTEXT_WIDGET:
        formfield_overrides = {
            models.TextField: {'widget': newsletter_settings.RICHTEXT_WIDGET},
        }


class PublicityInline(AdminImageMixin, StackedInline):
    model = Publicity
    extra = 1
    fieldsets = (
        (None, {
            'fields': ('title', 'sortorder', 'image', 'url')
        }),
    )

    if newsletter_settings.RICHTEXT_WIDGET:
        formfield_overrides = {
            models.TextField: {'widget': newsletter_settings.RICHTEXT_WIDGET},
        }


class MessageAdmin(AdminImageMixin, admin.ModelAdmin, ExtendibleModelAdminMixin):
    save_as = True
    list_display = (
        'admin_title', 'admin_newsletter', 'admin_preview', 'date_create',
        'date_modify'
    )
    list_filter = ('newsletter', )
    date_hierarchy = 'date_create'
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ArticleInline, PublicityInline]

    """ List extensions """

    def admin_title(self, obj):
        return '<a href="%d/">%s</a>' % (obj.id, obj.title)

    admin_title.short_description = ugettext('message')
    admin_title.allow_tags = True

    def admin_preview(self, obj):
        return '<a href="%d/preview/">%s</a>' % (obj.id, ugettext('Preview'))

    def admin_rss(self, obj):
        return '<a href="/rss/">%s</a>' % (ugettext('Rss'))

    admin_preview.short_description = ''
    admin_preview.allow_tags = True

    admin_rss.short_description = ''
    admin_rss.allow_tags = True

    def admin_newsletter(self, obj):
        return '<a href="../newsletter/%s/">%s</a>' % (
            obj.newsletter.id, obj.newsletter
        )

    admin_newsletter.short_description = ugettext('newsletter')
    admin_newsletter.allow_tags = True

    """ Views """

    def messages_rss(self, request, object_id):
        if request.POST:
            wraper = None
            choice = request.POST['choice']
            if int(choice):
                wraper = WrapperRSS('http://www.ain.cu/?format=feed&type=rss')
            else:
                wraper = WrapperRSS('http://www.cubadebate.cu/feed/')
            res = wraper.get_news()
            message = md.Message.objects.get(pk=int(object_id))
            for values in res:
                message.articles.add(Article(title=values[0], text=values[1], url=values[2]))
            message.save()
            return HttpResponseRedirect('/admin/newsletter/message/' + str(object_id))
        else:
            form = ['CubaDebate', 'AIN']

        return render_to_response(
            "admin/newsletter/message/rssform.html",
            {'form': form},
            RequestContext(request, {}),
        )

    def preview(self, request, object_id):
        return render_to_response(
            "admin/newsletter/message/preview.html",
            {'message': self._getobj(request, object_id)},
            RequestContext(request, {}),
        )

    @xframe_options_sameorigin
    def preview_html(self, request, object_id):
        message = self._getobj(request, object_id)

        (subject_template, text_template, html_template) = \
            message.newsletter.get_templates('message')

        if not html_template:
            raise Http404(_(
                'No HTML template associated with the newsletter this '
                'message belongs to.'
            ))

        # print (message.get_default_id())
        simple = False
        if message.publicities.all().__len__() < 7:
            simple = True

        news_pict = False

        try:
            new_image = sorl.thumbnail.get_thumbnail(message.image, '470x150')
            news_pict = new_image
        except:
            news_pict = False


        c = Context({'message': message,
                     'issue': message.get_default_id(),
                     'site': Site.objects.get_current(),
                     'newsletter': message.newsletter,
                     'date': now(),
                     'STATIC_URL': settings.STATIC_URL,
                     'MEDIA_URL': settings.MEDIA_URL,
                     'simple' : simple,
                     'newspict': news_pict,
        })

        return HttpResponse(html_template.render(c))

    @xframe_options_sameorigin
    def preview_text(self, request, object_id):
        message = self._getobj(request, object_id)

        (subject_template, text_template, html_template) = \
            message.newsletter.get_templates('message')

        c = Context({
                        'message': message,
                        'site': Site.objects.get_current(),
                        'newsletter': message.newsletter,
                        'date': now(),
                        'STATIC_URL': settings.STATIC_URL,
                        'MEDIA_URL': settings.MEDIA_URL
                    }, autoescape=False)

        return HttpResponse(text_template.render(c), mimetype='text/plain')

    def submit(self, request, object_id):
        submission = Submission.from_message(self._getobj(request, object_id))

        return HttpResponseRedirect('../../../submission/%s/' % submission.id)

    def subscribers_json(self, request, object_id):
        message = self._getobj(request, object_id)

        json = serializers.serialize(
            "json", message.newsletter.get_subscriptions(), fields=()
        )
        return HttpResponse(json, mimetype='application/json')

    """ URLs """

    def get_urls(self):
        urls = super(MessageAdmin, self).get_urls()

        my_urls = patterns(
            '',
            url(r'^(.+)/preview/$',
                self._wrap(self.preview),
                name=self._view_name('preview')),
            url(r'^(.+)/preview/html/$',
                self._wrap(self.preview_html),
                name=self._view_name('preview_html')),
            url(r'^(.+)/preview/text/$',
                self._wrap(self.preview_text),
                name=self._view_name('preview_text')),
            url(r'^(.+)/submit/$',
                self._wrap(self.submit),
                name=self._view_name('submit')),
            url(r'^(.+)/rss/$',
                self._wrap(self.messages_rss),
                name=self._view_name('messages_rss')),
            url(r'^(.+)/subscribers/json/$',
                self._wrap(self.subscribers_json),
                name=self._view_name('subscribers_json')),
        )

        return my_urls + urls


class SubscriptionAdmin(admin.ModelAdmin, ExtendibleModelAdminMixin):
    form = SubscriptionAdminForm
    list_display = (
        'name', 'email', 'admin_newsletter', 'admin_subscribe_date',
        'admin_unsubscribe_date', 'admin_status_text', 'admin_status'
    )
    list_display_links = ('name', 'email')
    list_filter = (
        'newsletter', 'subscribed', 'unsubscribed', 'subscribe_date'
    )
    search_fields = (
        'name_field', 'email_field', 'user__first_name', 'user__last_name',
        'user__email'
    )
    readonly_fields = (
        'ip', 'subscribe_date', 'unsubscribe_date', 'activation_code'
    )
    date_hierarchy = 'subscribe_date'
    actions = ['make_subscribed', 'make_unsubscribed']

    """ List extensions """

    def admin_newsletter(self, obj):
        return '<a href="../newsletter/%s/">%s</a>' % (
            obj.newsletter.id, obj.newsletter
        )

    admin_newsletter.short_description = ugettext('newsletter')
    admin_newsletter.allow_tags = True

    def admin_status(self, obj):
        if obj.unsubscribed:
            return u'<img src="%s" width="10" height="10" alt="%s"/>' % (
                ICON_URLS['no'], self.admin_status_text(obj))

        if obj.subscribed:
            return u'<img src="%s" width="10" height="10" alt="%s"/>' % (
                ICON_URLS['yes'], self.admin_status_text(obj))
        else:
            return u'<img src="%s" width="10" height="10" alt="%s"/>' % (
                ICON_URLS['wait'], self.admin_status_text(obj))

    admin_status.short_description = ''
    admin_status.allow_tags = True

    def admin_status_text(self, obj):
        if obj.subscribed:
            return ugettext("Subscribed")
        elif obj.unsubscribed:
            return ugettext("Unsubscribed")
        else:
            return ugettext("Unactivated")

    admin_status_text.short_description = ugettext('Status')

    def admin_subscribe_date(self, obj):
        if obj.subscribe_date:
            return date_format(obj.subscribe_date)
        else:
            return ''

    admin_subscribe_date.short_description = _("subscribe date")

    def admin_unsubscribe_date(self, obj):
        if obj.unsubscribe_date:
            return date_format(obj.unsubscribe_date)
        else:
            return ''

    admin_unsubscribe_date.short_description = _("unsubscribe date")

    """ Actions """

    def make_subscribed(self, request, queryset):
        rows_updated = queryset.update(subscribed=True)
        self.message_user(
            request,
            ungettext(
                "%s user has been successfully subscribed.",
                "%s users have been successfully subscribed.",
                rows_updated
            ) % rows_updated
        )

    make_subscribed.short_description = _("Subscribe selected users")

    def make_unsubscribed(self, request, queryset):
        rows_updated = queryset.update(subscribed=False)
        self.message_user(
            request,
            ungettext(
                "%s user has been successfully unsubscribed.",
                "%s users have been successfully unsubscribed.",
                rows_updated
            ) % rows_updated
        )

    make_unsubscribed.short_description = _("Unsubscribe selected users")

    """ Views """

    def subscribers_import(self, request):
        if request.POST:
            form = ImportForm(request.POST, request.FILES)
            if form.is_valid():
                # request.session['addresses'] = form.get_addresses()
                # THE PROBLEM IS HERE
                #VER COMO LO MANDO A /newsletter/subscription/
                #EL PROBLEMA ESTA EN EL form (HAY ALGO RARO CON ESTO)
                return HttpResponseRedirect('/admin/newsletter/subscription/')
                #return HttpResponseRedirect('confirm/')
        else:
            form = ImportForm()

        return render_to_response(
            "admin/newsletter/subscription/importform.html",
            {'form': form},
            RequestContext(request, {}),
        )

    def subscribers_import_confirm(self, request):
        print('entro a este method')
        # If no addresses are in the session, start all over.
        if not 'addresses' in request.session:
            return HttpResponseRedirect('../')

        addresses = request.session['addresses']
        logger.debug('Confirming addresses: %s', addresses)
        if request.POST:
            form = ConfirmForm(request.POST)
            if form.is_valid():
                try:
                    for address in addresses.values():
                        address.save()
                finally:
                    del request.session['addresses']

                messages.success(
                    request,
                    _('%s subscriptions have been successfully added.') %
                    len(addresses)
                )

                return HttpResponseRedirect('../../')
        else:
            form = ConfirmForm()

        return render_to_response(
            "admin/newsletter/subscription/confirmimportform.html",
            {'form': form, 'subscribers': addresses},
            RequestContext(request, {}),
        )

    """ URLs """

    def get_urls(self):
        urls = super(SubscriptionAdmin, self).get_urls()

        my_urls = patterns(
            '',
            url(r'^import/$',
                self._wrap(self.subscribers_import),
                name=self._view_name('import')),
            url(r'^import/confirm/$',
                self._wrap(self.subscribers_import_confirm),
                name=self._view_name('import_confirm')),

            # Translated JS strings - these should be app-wide but are
            # only used in this part of the admin. For now, leave them here.
            url(r'^jsi18n/$',
                'django.views.i18n.javascript_catalog',
                {'packages': ('newsletter',)},
                name='newsletter_js18n')
        )

        return my_urls + urls


admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
