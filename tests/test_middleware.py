import jwt
import pytest
from aiohttp import web

from aiohttp_jwt import JWTMiddleware


@pytest.fixture
def create_app(secret):
    def factory(routes, *args, **kwargs):
        defaults = {'secret_or_pub_key': secret}
        app = web.Application(
            middlewares=[
                JWTMiddleware(
                    *args,
                    **{
                        **defaults,
                        **kwargs
                    },
                ),
            ],
        )

        for path, handler in routes:
            app.router.add_get(path, handler)

        return app
    return factory


def test_throw_on_invalid_secret():
    with pytest.raises(ValueError):
        JWTMiddleware(secret_or_pub_key='')


async def test_get_payload(create_app, aiohttp_client, fake_payload, token):
    async def handler(request):
        assert request.get('payload') == fake_payload
        return web.json_response({'status': 'ok'})
    routes = (('/foo', handler),)
    client = await aiohttp_client(create_app(routes))
    response = await client.get('/foo', headers={
        'Authorization': 'Bearer {}'.format(token.decode('utf-8')),
    })
    assert response.status == 200


async def test_unauthorized_on_missing_token(
        create_app, aiohttp_client, fake_payload, token):
    async def handler(request):
        return web.json_response({})
    routes = (('/foo', handler),)
    client = await aiohttp_client(create_app(routes))
    response = await client.get('/foo')
    assert response.status == 401
    assert 'Missing authorization' in response.reason


async def test_forbidden_on_wrong_secret(
        create_app, aiohttp_client, fake_payload):
    async def handler(request):
        return web.json_response({})
    routes = (('/foo', handler),)
    client = await aiohttp_client(create_app(routes))
    token = jwt.encode(fake_payload, 'wrong').decode('utf-8')
    response = await client.get('/foo', headers={
        'Authorization': 'Bearer {}'.format(token),
    })
    assert response.status == 403
    assert 'Invalid authorization' in response.reason


async def test_credentials_not_required(
        create_app, aiohttp_client, fake_payload):
    async def handler(request):
        return web.json_response({})
    routes = (('/foo', handler),)
    client = await aiohttp_client(
        create_app(routes, credentials_required=False),
    )
    response = await client.get('/foo')
    assert response.status == 200


async def test_whitelisted_path(create_app, aiohttp_client, fake_payload):
    async def handler(request):
        return web.json_response({})
    routes = (('/foo', handler),)
    client = await aiohttp_client(
        create_app(routes, whitelist=[r'/foo*']),
    )
    response = await client.get('/foo')
    assert response.status == 200


async def test_custom_request_property(
        create_app, aiohttp_client, fake_payload, token):
    request_property = 'custom'

    async def handler(request):
        assert request.get(request_property) == fake_payload
        return web.json_response({})

    routes = (('/foo', handler),)
    client = await aiohttp_client(
        create_app(
            routes,
            request_property=request_property,
        ),
    )
    response = await client.get('/foo', headers={
        'Authorization': 'Bearer {}'.format(token.decode('utf-8')),
    })
    assert response.status == 200
    assert (await response.json()) == {}


async def test_storing_token(create_app, aiohttp_client, fake_payload, token):
    token_property = 'token'

    async def handler(request):
        assert request.get(token_property) == token
        return web.json_response({})

    routes = (('/foo', handler),)
    client = await aiohttp_client(
        create_app(routes, store_token=token_property),
    )
    response = await client.get('/foo', headers={
        'Authorization': 'Bearer {}'.format(token.decode('utf-8')),
    })
    assert response.status == 200
    assert (await response.json()) == {}
