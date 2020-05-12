#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: identity.py 110862 2017-04-18 00:30:43Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import hashlib
import requests

import pyramid.httpexceptions as hexc

from pyramid.interfaces import IRequest

from pyramid.view import view_config

from requests.exceptions import RequestException

from requests.structures import CaseInsensitiveDict

from six.moves import urllib_parse

from simplejson import JSONDecodeError

from zope import interface
from zope import component

from zope.event import notify

from nti.app.products.salesforce import MessageFactory as _

from nti.app.products.salesforce.interfaces import ISalesforceLogonSettings
from nti.app.products.salesforce.interfaces import SalesforceUserLogonEvent
from nti.app.products.salesforce.interfaces import SalesforceUserCreatedEvent

from nti.app.products.salesforce.utils import set_user_salesforce_id
from nti.app.products.salesforce.utils import get_user_for_salesforce_id

from nti.appserver.interfaces import IMissingUser
from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.appserver.logon import _create_success_response
from nti.appserver.logon import _create_failure_response
from nti.appserver.logon import _deal_with_external_account

from nti.appserver.policies.interfaces import INoAccountCreationEmail

from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users.interfaces import IUsernameGeneratorUtility

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import force_email_verification

from nti.links.links import Link

logger = __import__('logging').getLogger(__name__)

#: The initial SALESFORCE login rel
REL_LOGIN_SALESFORCE = 'logon.salesforce'

#: The redirect rel after SALESFORCE auth
LOGON_SALESFORCE = 'logon.salesforce.oauth2'

SALESFORCE_RETURN_URL_PARAM = 'redirect_uri'

# Saw timeouts at 1 second
_REQUEST_TIMEOUT = 4.0


def redirect_salesforce_uri(request):
    root = request.route_path('objects.generic.traversal', traverse=())
    root = root[:-1] if root.endswith('/') else root
    target = urllib_parse.urljoin(request.application_url, root)
    target = target + '/' if not target.endswith('/') else target
    target = urllib_parse.urljoin(target, LOGON_SALESFORCE)
    return target


def redirect_salesforce2_params(request, state=None):
    state = state or hashlib.sha256(os.urandom(1024)).hexdigest()
    auth_settings = component.getUtility(ISalesforceLogonSettings)
    params = {'state': state,
              'response_type': 'code',
              'client_id': auth_settings.client_id,
               SALESFORCE_RETURN_URL_PARAM: redirect_salesforce_uri(request)}
    return params


def generate_username():
    username_util = component.getUtility(IUsernameGeneratorUtility)
    return username_util.generate_username()


def _get_auth_url():
    auth_settings = component.getUtility(ISalesforceLogonSettings)
    auth_url = auth_settings.login_url
    return auth_url[:-1] if auth_url.endswith('/') else auth_url


@view_config(name=REL_LOGIN_SALESFORCE,
             route_name='objects.generic.traversal',
             context=IDataserverFolder,
             request_method='GET',
             renderer='rest')
def salesforce_oauth(request, success=None, failure=None, state=None):
    state = state or hashlib.sha256(os.urandom(1024)).hexdigest()
    params = redirect_salesforce2_params(request, state)

    for key, value in (('success', success), ('failure', failure)):
        value = value or request.params.get(key)
        if value:
            request.session['salesforce.' + key] = value

    # save state for validation
    request.session['salesforce.state'] = state

    # redirect
    target = _get_auth_url()
    target = '%s?%s' % (target, urllib_parse.urlencode(params))
    response = hexc.HTTPSeeOther(location=target)
    return response


def _return_url(request, url_type='success'):
    if url_type in request.params:
        return request.params.get(url_type)
    return request.session.get('salesforce.' + url_type)


@view_config(name=LOGON_SALESFORCE,
             route_name='objects.generic.traversal',
             context=IDataserverFolder,
             request_method='GET',
             renderer='rest')
def salesforce_oauth2(request):
    params = request.params
    # check for errors
    if 'error' in params or 'errorCode' in params:
        error = params.get('error') or params.get('errorCode')
        logger.warn('Salesforce error during oauth (%s)', error)
        return _create_failure_response(request,
                                        _return_url(request, 'failure'),
                                        error=error)

    # Confirm anti-forgery state token
    if not request.session.get('salesforce.state'):
        return _create_failure_response(request,
                                        _return_url(request, 'failure'),
                                        error=_(u'Missing state.'))
    if 'state' in params:
        params_state = params.get('state')
        session_state = request.session.get('salesforce.state')
        if params_state != session_state:
            return _create_failure_response(request,
                                            _return_url(request, 'failure'),
                                            error=_(u'Incorrect state values.'))

    code = params.get('code')

    if not code:
        logger.warn('Salesforce code not found after oauth')
        return _create_failure_response(request,
                                        _return_url(request, 'failure'),
                                        error=_(u'Could not find Salesforce code.'))

    # Get our access token
    auth_settings = component.getUtility(ISalesforceLogonSettings)
    data = {'grant_type': 'authorization_code',
            'client_id': auth_settings.client_id,
            'client_secret': auth_settings.client_secret,
             SALESFORCE_RETURN_URL_PARAM: redirect_salesforce_uri(request),
            'code': code}
    auth = requests.post(auth_settings.token_url,
                         data=data,
                         timeout=_REQUEST_TIMEOUT)

    try:
        auth.raise_for_status()
    except RequestException as req_ex:
        logger.exception("Failed salesforce login %s", auth.text)
        return _create_failure_response(request,
                                        _return_url(request, 'failure'),
                                        error=str(req_ex))

    data = auth.json()
    if 'access_token' not in data:
        return _create_failure_response(request,
                                        _return_url(request, 'failure'),
                                        error=_(u'Could not find access token.'))
    access_token = data['access_token']
    try:
        logger.debug("Getting user profile")
        response = requests.get(auth_settings.user_info_url,
                                params={"access_token": access_token,
                                        "format": "json"})

        try:
            response.raise_for_status()
        except RequestException as req_ex:
            logger.exception("Failed to fetch salesforce user info")
            return _create_failure_response(request,
                                            request.cookies.get(
                                                'salesforce.failure'),
                                            error=str(req_ex))

        try:
            user_info = CaseInsensitiveDict(response.json())
        except JSONDecodeError:
            # Code error? They are not giving us json
            logger.warn("Invalid user info (%s) (%s)",
                        response.status_code, response.text)
            return _create_failure_response(request,
                                            request.cookies.get(
                                                'salesforce.failure'),
                                            error=_(u'Invalid user info.'))
        if     not user_info.get('email') \
            or not user_info.get('name') \
            or not user_info.get('user_id'):
                logger.exception("Invalid salesforce user info (%s)", user_info)
                return _create_failure_response(request,
                                                request.cookies.get('salesforce.failure'),
                                                error=_(u'Invalid user info.'))
        external_id = str(user_info.get('user_id'))
        user = get_user_for_salesforce_id(external_id)
        if user is None:
            username = generate_username()
            interface.alsoProvides(request, INoAccountCreationEmail)
            user = _deal_with_external_account(request,
                                               fname=None,
                                               lname=None,
                                               username=username,
                                               realname=user_info.get('name'),
                                               email=user_info.get('email'),
                                               idurl=None,
                                               iface=None,
                                               user_factory=User.create_user,
                                               ext_values=user_info)
            set_user_salesforce_id(user, external_id, request)
            force_email_verification(user)  # trusted source
            notify(SalesforceUserCreatedEvent(user, request))
            request.environ['nti.request_had_transaction_side_effects'] = 'True'

        notify(SalesforceUserLogonEvent(user, user_info))
        response = _create_success_response(request,
                                            userid=user.username,
                                            success=_return_url(request),)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception('Failed to login with salesforce')
        response = _create_failure_response(request,
                                            _return_url(request, 'failure'),
                                            error=str(e))
    return response


@component.adapter(IRequest)
@interface.implementer(IUnauthenticatedUserLinkProvider)
class SimpleUnauthenticatedUserSalesforceLinkProvider(object):

    rel = REL_LOGIN_SALESFORCE

    default_title = _('Logon through Salesforce')

    def __init__(self, request):
        self.request = request

    @property
    def title(self):
        auth_settings = component.queryUtility(ISalesforceLogonSettings)
        if auth_settings is not None:
            return auth_settings.logon_link_title or self.default_title

    def get_links(self):
        auth_settings = component.queryUtility(ISalesforceLogonSettings)
        result = []
        if auth_settings is not None:
            elements = (self.rel,)
            root = self.request.route_path('objects.generic.traversal',
                                           traverse=())
            root = root[:-1] if root.endswith('/') else root
            result.append(Link(root, elements=elements, rel=self.rel, title=self.title))
        return result


@interface.implementer(ILogonLinkProvider)
@component.adapter(IMissingUser, IRequest)
class SimpleMissingUserSalesforceLinkProvider(SimpleUnauthenticatedUserSalesforceLinkProvider):

    def __init__(self, user, request):
        super(SimpleMissingUserSalesforceLinkProvider, self).__init__(request)
        self.user = user

    def __call__(self):
        links = self.get_links()
        return links[0] if links else None
