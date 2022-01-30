from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, BooleanField, PasswordField
from wtforms.validators import DataRequired

# class HostNetworkForm(FlaskForm):
#     username = StringField('username', validators=[DataRequired()])
#     password = PasswordField('password', validators=[DataRequired()])
#     protocol = StringField('protocol', validators=[DataRequired()])
#     host = StringField('host', validators=[DataRequired()])
#     port = IntegerField('port', validators=[DataRequired()])
#     client_id = StringField('client_id', validators=[])
#     client_secret = StringField('client_secret', validators=[])
#     ssl_check = BooleanField('ssl_check', validators=[])
#     submit = SubmitField()

        # <!-- <form action="" method="post" novalidate>
        #     {{ form.hidden_tag() }}
        #     {{ form.csrf_token }}
        #     <p>
        #         {{ form.username.label }}<br>
        #         {{ form.username(size=32) }}<br>
        #         {{ form.password.label }}<br>
        #         {{ form.password(size=32) }}<br>
        #         {{ form.protocol.label }}<br>
        #         {{ form.protocol(size=32) }}<br>
        #         {{ form.host.label }}<br>
        #         {{ form.host(size=32) }}<br>
        #         {{ form.port.label }}<br>
        #         {{ form.port(size=32) }}<br>
        #         {{ form.client_id.label }}<br>
        #         {{ form.client_id(size=32) }}<br>
        #         {{ form.client_secret.label }}<br>
        #         {{ form.client_secret(size=32) }}<br>
        #         {{ form.ssl_check.label }}<br>
        #         {{ form.ssl_check(size=32) }}
        #     </p>
        #     <p>{{ form.submit() }}</p>
        # </form> -->


class ClientNetworkForm(FlaskForm):
    token = PasswordField('token', validators=[DataRequired()])
    # protocol = StringField('protocol', validators=[DataRequired()])
    # host = StringField('host', validators=[DataRequired()])
    # port = IntegerField('port', validators=[DataRequired()])
    ssl_check = BooleanField('ssl_check', validators=[])
    submit_client = SubmitField()

class RemoteNetworkForm(FlaskForm):
    token = PasswordField('token', validators=[DataRequired()])
    # protocol = StringField('protocol', validators=[DataRequired()])
    host = StringField('host', validators=[DataRequired()])
    port = IntegerField('port', validators=[DataRequired()])
    ssl_check = BooleanField('ssl_check', validators=[])
    submit_central = SubmitField()
    