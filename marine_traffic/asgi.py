import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marine_traffic.settings')

# Django MUST be initialized before any app imports
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from django.conf import settings
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from marine_traffic.routing import websocket_urlpatterns

# En développement : daphne ne sert pas les static files nativement
# ASGIStaticFilesHandler les ajoute automatiquement quand DEBUG=True
if settings.DEBUG:
    from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
    http_app = ASGIStaticFilesHandler(django_asgi_app)
else:
    http_app = django_asgi_app

application = ProtocolTypeRouter({
    'http':      http_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
