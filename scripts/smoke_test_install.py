"""Run outside the checkout to verify an installed wheel can serve Django assets."""
from importlib import import_module, metadata
from pathlib import Path

import django
from django.conf import settings

import django_stripe


root = Path(__file__).resolve().parents[1]
installed = Path(django_stripe.__file__).resolve()
if installed.is_relative_to(root):
    raise SystemExit(f'Imported checkout instead of installed wheel: {installed}')
assert django_stripe.__version__ == metadata.version('django-stripe-subs')
settings.configure(
    SECRET_KEY='distribution-smoke-test',
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes',
                    'django.contrib.staticfiles', 'rest_framework', 'django_stripe'],
    TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True}],
    STATIC_URL='/static/',
)
django.setup()
from django.contrib.staticfiles import finders
from django.template.loader import get_template

import_module('django_stripe.templatetags.number_formats')
import_module('django_stripe.migrations')
for name in ('base_portal', 'checkout', 'subscription_portal', 'subscription_history'):
    get_template(f'django_stripe/{name}.html')
for name in ('js/django_stripe/payments.js', 'css/django_stripe/store.css',
             'images/django_stripe/logo.png', 'images/django_stripe/cards/visa.svg'):
    assert finders.find(name), f'Missing static asset: {name}'
print(f'Installed {django_stripe.__version__}: templates, template tags, migrations and static assets OK')
