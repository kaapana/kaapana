from ast import alias
import json
import uuid

from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Request, HTTPException

from . import models
from urllib.parse import urlparse

