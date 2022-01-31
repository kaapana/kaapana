from flask_wtf import FlaskForm
from wtforms import widgets, StringField, SubmitField, IntegerField, BooleanField, PasswordField, SelectMultipleField
from wtforms.validators import DataRequired

from app.utils import get_dag_list, get_dataset_list

class MultiCheckboxField(SelectMultipleField):
    #https://gist.github.com/ectrimble20/468156763a1389a913089782ab0f272e
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class ClientNetworkForm(FlaskForm):
    # protocol = StringField('protocol', validators=[DataRequired()])
    # host = StringField('host', validators=[DataRequired()])
    # port = IntegerField('port', validators=[DataRequired()])
    ssl_check = BooleanField('SSL Check', validators=[])
    allowed_dags = MultiCheckboxField('Select dags that can be triggered from remote.', choices=[(dag, dag) for dag in sorted(get_dag_list()) if not dag.startswith('service')])
    allowed_datasets = MultiCheckboxField('Select datasets that can be used from remote.', choices=[(dataset, dataset) for dataset in sorted(list(set([d for datasets in get_dataset_list() for d in datasets])))])

    fernet_encrypted = BooleanField('Fernet encrypted', validators=[])
    submit_client = SubmitField('Generated client network configuration')

class RemoteNetworkForm(FlaskForm):
    token = PasswordField('Token', validators=[DataRequired()])
    # protocol = StringField('protocol', validators=[DataRequired()])
    host = StringField('Host', validators=[DataRequired()])
    port = IntegerField('Port', validators=[DataRequired()])
    fernet_key = PasswordField('Fernet key', validators=[])
    ssl_check = BooleanField('SSL Check', validators=[])
    submit_central = SubmitField('Submit central network configuration')
