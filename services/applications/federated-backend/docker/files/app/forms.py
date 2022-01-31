from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, BooleanField, PasswordField
from wtforms.validators import DataRequired

class ClientNetworkForm(FlaskForm):
    # protocol = StringField('protocol', validators=[DataRequired()])
    # host = StringField('host', validators=[DataRequired()])
    # port = IntegerField('port', validators=[DataRequired()])
    ssl_check = BooleanField('SSL Check', validators=[])
    fernet_encrypted = BooleanField('Fernet encrypted', validators=[])
    submit_client = SubmitField('Generated client network configuration')

class RemoteNetworkForm(FlaskForm):
    token = PasswordField('Token', validators=[DataRequired()])
    # protocol = StringField('protocol', validators=[DataRequired()])
    host = StringField('Host', validators=[DataRequired()])
    port = IntegerField('Port', validators=[DataRequired()])
    fernet_key = PasswordField('Fernet key', validators=[DataRequired()])
    ssl_check = BooleanField('SSL Check', validators=[])
    submit_central = SubmitField('Submit central network configuration')
