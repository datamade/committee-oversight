# SECURITY WARNING: keep the secret key used in production secret!
# Set this to an arbitrary string
SECRET_KEY = '*mb&wj8q@n5jy!fki)qi*%@i=+gc7v1$a7*v*=bj&xktxi0g&b'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'hearings',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}