from app import db
from flask_login import UserMixin

# class HostNetwork(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(64), index=True, unique=True)
#     password = db.Column(db.String(64), index=True, unique=True)
#     protocol = db.Column(db.String(64), index=True, unique=True)
#     host = db.Column(db.String(64), index=True, unique=True)
#     port = db.Column(db.Integer(), index=True, unique=True)
#     client_id = db.Column(db.String(64), index=True, unique=True)
#     client_secret = db.Column(db.String(64), index=True, unique=True)
#     ssl_check = db.Column(db.Boolean(), index=True, unique=True)

#     def __repr__(self):
#         return '<HostNetwork {}://{}:{}>'.format(self.protocol, self.host, self.port)

class ClientNetwork(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100))
    protocol = db.Column(db.String(64), index=True, unique=True)
    host = db.Column(db.String(64), index=True, unique=True)
    port = db.Column(db.Integer(), index=True, unique=True)
    ssl_check = db.Column(db.Boolean(), index=True, unique=True)

    def __repr__(self):
        return '<ClientNetwork {}://{}:{}>'.format(self.protocol, self.host, self.port)

class RemoteNetwork(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100))
    protocol = db.Column(db.String(64), index=True, unique=True)
    host = db.Column(db.String(64), index=True, unique=True)
    port = db.Column(db.Integer(), index=True, unique=True)
    ssl_check = db.Column(db.Boolean(), index=True, unique=True)

    def __repr__(self):
        return '<RemoteNetwork {}://{}:{}>'.format(self.protocol, self.host, self.port)