# -*- coding: utf-8 -
#
# This file is part of dj-webmachine released under the MIT license. 
# See the NOTICE for more information.

from django.template import loader, RequestContext
import oauth2

from webmachine.forms import OAuthAuthenticationForm
from webmachine.resource import Resource


class Oauth(Resource):

    def __init__(self, realm='OAuth', 
            auth_template='webmachine/authorize_token.html', 
            auth_form=OAuthAuthenticationForm, name=None, 
            app_name='webmachine'):

        self.auth_template = auth_template
        self.auth_form = auth_form
        self.realm = realm
        self.name = name or 'oauth'
        self.app_name = app_name

    def allowed_methods(self, req, resp):
        return ["GET", "HEAD", "POST"]
    
    def oauth_authorize(self, req, resp):
        try:
            token = oauth_server.fetch_request_token(req.oauth_request)
        except oauth.OAuthError, err:
            return self.auth_error(req, resp, err)
        return send_oauth_error(err)
        
        try:
            callback = req.auth_server.get_callback(oauth_request)
        except:
            callback = None
    
        if req.method == "GET":
            params = req.oauth_request.get_normalized_parameters()
            form = self.auth_form(initial={
                'oauth_token': token.key,
                'oauth_callback': token.get_callback_url() or callback,
            })
            resp.content = loader.render_to_string(self.auth_template, 
                    { 'form': form }, RequestContext(req))

        elif req.method == "POST":
            try:
                form = self.auth_form(req.POST)
                if form.is_valid():
                    token = req.oauth_server.authorize_token(token, req.user)
                    args = '?'+token.to_string(only_key=True)
                else:
                    args = '?error=%s' % 'Access not granted by user.'
            
                if not callback:
                    return True 
               
                resp.redirect_to = iri_to_uri("%s%s" % (callback, args))
            except oauth2.Error, err:
                return self.oauth_error(req, resp, err)
        return True

    def oauth_access_token(self, req, resp):
        try:
            token = oauth_server.fetch_access_token(req.oauth_request)
            resp.content = token.to_string()
        except oauth.Error, err:
            return self.oauth_error(req, resp, err)
        return True

    def oauth_request_token(self, req, resp):
        try:
            token = oauth_server.fetch_request_token(req.oauth_request)
            resp.content = token.to_string()
        except oauth.Error, err:
            return self.oauth_error(req, resp, err) 
        return True

    def oauth_error(self, req, resp, err):
        resp.content = str(err)
        return 'OAuth realm="%s"' % self.realm

    def process_post(self, res, resp):
        # we already processed POST
        return True

    def created_location(self, req, resp):
        try:
            return resp.redirect_to
        except AttributeError:
            return False
 
    def is_unauthorized(self, req, resp):
        func = getattr(self, "oauth_%s" % req.oauth_action)
        return func(req, resp)

    def malformed_request(self, req, resp):
        params = {}
        headers = {}

        if req.method == "POST":
            params = req.REQUEST.items()

        if 'HTTP_AUTHORIZATION' in req.META:
            headers['Authorization'] = req.META.get('HTTP_AUTHORIZATION')

        oauth_request = oauth2.Request.from_request(req.method, 
            req.build_absolute_uri(), headers=headers,
            parameters=params,
            query_string=req.META.get('QUERY_STRING'))

        if not oauth_request:
            return False

        req.oauth_request = oauth_request
        return True

    def resource_exists(self, req, resp):
        action = req.url_kwargs.get("action")
        if not action or action not in ("authorize", "access_token",
                "request_token"):
            return False
        req.oauth_action = action

        return True

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urlpatterns = patterns('', 
                url(r'^authorize$', self, {"action": "authorize"}, 
                    name="oauth_authorize"),
                url(r'^access_token$', self, {"action": "access_token"},
                    name="oauth_access_token"),
                url(r'^request_token$', self, {"action": "request_token"},
                    name="oauth_request_token")
        )
        return urlpatterns

    def urls(self):
        return self.get_urls(), self.app_name, self.name
    urls = property(urls)

    
