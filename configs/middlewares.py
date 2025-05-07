import os


# Standard Django Middleware
DJANGO_MIDDLEWARE = [
    # packages

    # django
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Custom Middleware
CUSTOM_MIDDLEWARE = [
    'common.middleware.HandleObjectExistMiddleware',
    'common.middleware.HandleObjectDoesNotExistMiddleware',
    'common.middleware.HandleExceptionMiddleware',
]

# Debug Middleware
DEBUG_MIDDLEWARE = [
    # 'any'
]


MIDDLEWARE = DJANGO_MIDDLEWARE + CUSTOM_MIDDLEWARE
if os.environ.get('DJANGO_DEBUG', 'False') == 'True':
    MIDDLEWARE += DEBUG_MIDDLEWARE
