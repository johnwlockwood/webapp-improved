# -*- coding: utf-8 -*-
"""
Tests for extra routes not included in webapp2 (see extras/routes.py)
"""
import random
import unittest

from webapp2 import (RedirectHandler, Request, RequestHandler, Route, Router,
    WSGIApplication)

from webtest import TestApp

from extras.routes import (DomainRoute, HandlerPrefixRoute, ImprovedRoute,
    NamePrefixRoute, PathPrefixRoute)

import test_base


class HomeHandler(RequestHandler):
    def get(self, **kwargs):
        self.response.out.write('home sweet home')


app = WSGIApplication([
    ImprovedRoute('/redirect-me-easily', redirect_to='/i-was-redirected-easily'),
    ImprovedRoute('/redirect-me-easily2', redirect_to='/i-was-redirected-easily', defaults={'permanent': False}),
    ImprovedRoute('/strict-foo', HomeHandler, 'foo-strict', strict_slash=True),
    ImprovedRoute('/strict-bar/', HomeHandler, 'bar-strict', strict_slash=True),
], debug=False)

test_app = TestApp(app)


class TestImprovedRoute(test_base.BaseTestCase):
    def test_route_redirect_to(self):
        route = ImprovedRoute('/foo', redirect_to='/bar')
        router = Router(None, [route])
        route_match, args, kwargs = router.match(Request.blank('/foo'))
        self.assertEqual(route_match, route)
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'url': '/bar'})

    def test_easy_redirect_to(self):
        res = test_app.get('/redirect-me-easily')
        self.assertEqual(res.status, '301 Moved Permanently')
        self.assertEqual(res.body, '')
        self.assertEqual(res.headers['Location'], 'http://localhost/i-was-redirected-easily')

        res = test_app.get('/redirect-me-easily2')
        self.assertEqual(res.status, '302 Found')
        self.assertEqual(res.body, '')
        self.assertEqual(res.headers['Location'], 'http://localhost/i-was-redirected-easily')

    def test_strict_slash(self):
        res = test_app.get('/strict-foo')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.body, 'home sweet home')

        res = test_app.get('/strict-bar/')
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.body, 'home sweet home')

        # Now the non-strict...

        res = test_app.get('/strict-foo/')
        self.assertEqual(res.status, '301 Moved Permanently')
        self.assertEqual(res.body, '')
        self.assertEqual(res.headers['Location'], 'http://localhost/strict-foo')

        res = test_app.get('/strict-bar')
        self.assertEqual(res.status, '301 Moved Permanently')
        self.assertEqual(res.body, '')
        self.assertEqual(res.headers['Location'], 'http://localhost/strict-bar/')


class TestPrefixRoutes(test_base.BaseTestCase):
    def test_simple(self):
        router = Router(None, [
            PathPrefixRoute('/a', [
                Route('/', 'a', 'name-a'),
                Route('/b', 'a/b', 'name-a/b'),
                Route('/c', 'a/c', 'name-a/c'),
                PathPrefixRoute('/d', [
                    Route('/', 'a/d', 'name-a/d'),
                    Route('/b', 'a/d/b', 'name-a/d/b'),
                    Route('/c', 'a/d/c', 'name-a/d/c'),
                ]),
            ])
        ])

        path = '/a/'
        match = ((), {})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('name-a', Request.blank('/'), match[0], match[1]), path)

        path = '/a/b'
        match = ((), {})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('name-a/b', Request.blank('/'), match[0], match[1]), path)

        path = '/a/c'
        match = ((), {})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('name-a/c', Request.blank('/'), match[0], match[1]), path)

        path = '/a/d/'
        match = ((), {})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('name-a/d', Request.blank('/'), match[0], match[1]), path)

        path = '/a/d/b'
        match = ((), {})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('name-a/d/b', Request.blank('/'), match[0], match[1]), path)

        path = '/a/d/c'
        match = ((), {})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('name-a/d/c', Request.blank('/'), match[0], match[1]), path)

    def test_with_variables_name_and_handler(self):
        router = Router(None, [
            PathPrefixRoute('/user/<username:\w+>', [
                HandlerPrefixRoute('apps.users.', [
                    NamePrefixRoute('user-', [
                        Route('/', 'UserOverviewHandler', 'overview'),
                        Route('/profile', 'UserProfileHandler', 'profile'),
                        Route('/projects', 'UserProjectsHandler', 'projects'),
                    ]),
                ]),
            ])
        ])

        path = '/user/calvin/'
        match = ((), {'username': 'calvin'})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('user-overview', Request.blank('/'), match[0], match[1]), path)

        path = '/user/calvin/profile'
        match = ((), {'username': 'calvin'})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('user-profile', Request.blank('/'), match[0], match[1]), path)

        path = '/user/calvin/projects'
        match = ((), {'username': 'calvin'})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        self.assertEqual(router.build('user-projects', Request.blank('/'), match[0], match[1]), path)


class TestDomainRoute(test_base.BaseTestCase):
    def test_simple(self):
        SUBDOMAIN_RE = '^([^.]+)\.app-id\.appspot\.com$'

        router = Router(None, [
            DomainRoute(SUBDOMAIN_RE, [
                Route('/foo', 'FooHandler', 'subdomain-thingie'),
            ])
        ])

        match = router.match(Request.blank('/foo'))
        self.assertEqual(match, None)

        match = router.match(Request.blank('http://my-subdomain.app-id.appspot.com/foo'))
        self.assertEqual(match[1:], ((), {'_host_match': ('my-subdomain',)}))

        match = router.match(Request.blank('http://another-subdomain.app-id.appspot.com/foo'))
        self.assertEqual(match[1:], ((), {'_host_match': ('another-subdomain',)}))

        url = router.build('subdomain-thingie', None, (), {'_netloc': 'another-subdomain.app-id.appspot.com'})
        self.assertEqual(url, 'http://another-subdomain.app-id.appspot.com/foo')

    def test_with_variables_name_and_handler(self):
        SUBDOMAIN_RE = '^([^.]+)\.app-id\.appspot\.com$'

        router = Router(None, [
            DomainRoute(SUBDOMAIN_RE, [
                PathPrefixRoute('/user/<username:\w+>', [
                    HandlerPrefixRoute('apps.users.', [
                        NamePrefixRoute('user-', [
                            Route('/', 'UserOverviewHandler', 'overview'),
                            Route('/profile', 'UserProfileHandler', 'profile'),
                            Route('/projects', 'UserProjectsHandler', 'projects'),
                        ]),
                    ]),
                ])
            ]),
        ])

        path = 'http://my-subdomain.app-id.appspot.com/user/calvin/'
        match = ((), {'username': 'calvin', '_host_match': ('my-subdomain',)})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        match[1].pop('_host_match')
        match[1]['_netloc'] = 'my-subdomain.app-id.appspot.com'
        self.assertEqual(router.build('user-overview', Request.blank('/'), match[0], match[1]), path)

        path = 'http://my-subdomain.app-id.appspot.com/user/calvin/profile'
        match = ((), {'username': 'calvin', '_host_match': ('my-subdomain',)})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        match[1].pop('_host_match')
        match[1]['_netloc'] = 'my-subdomain.app-id.appspot.com'
        self.assertEqual(router.build('user-profile', Request.blank('/'), match[0], match[1]), path)

        path = 'http://my-subdomain.app-id.appspot.com/user/calvin/projects'
        match = ((), {'username': 'calvin', '_host_match': ('my-subdomain',)})
        self.assertEqual(router.match(Request.blank(path))[1:], match)
        match[1].pop('_host_match')
        match[1]['_netloc'] = 'my-subdomain.app-id.appspot.com'
        self.assertEqual(router.build('user-projects', Request.blank('/'), match[0], match[1]), path)


if __name__ == '__main__':
    test_base.main()
