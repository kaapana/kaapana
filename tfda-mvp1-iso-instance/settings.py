# -*- coding: utf-8 -*-
from decouple import config

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

# flask mail config

# MAIL_SERVER = "smtp.gmail.com"
# MAIL_PORT = 465
# MAIL_USE_SSL = True
# MAIL_USERNAME = config("MAIL_USERNAME")
# MAIL_PASSWORD = config("EMAIL_PWD")
# MAIL_DEFAULT_SENDER = config("MAIL_SENDER")
