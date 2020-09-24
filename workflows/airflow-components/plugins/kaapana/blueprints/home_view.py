import ast
import codecs
import copy
import datetime as dt
import itertools
import json
import logging
import math
import os
import pickle
import traceback
from collections import defaultdict
from datetime import timedelta
from functools import wraps
from textwrap import dedent

from six.moves.urllib.parse import quote

import markdown
import pendulum
import sqlalchemy as sqla
from flask import (
    abort, jsonify, redirect, url_for, request, Markup, Response,
    current_app, render_template, make_response)
from flask import flash
from flask_admin import BaseView, expose, AdminIndexView
from flask_admin.actions import action
from flask_admin.babel import lazy_gettext
from flask_admin.contrib.sqla import ModelView
from flask_admin.form.fields import DateTimeField
from flask_admin.tools import iterdecode
import lazy_object_proxy
from jinja2 import escape
from jinja2.sandbox import ImmutableSandboxedEnvironment
from past.builtins import basestring
from pygments import highlight, lexers
from pygments.formatters import HtmlFormatter
import six
from sqlalchemy import or_, desc, and_, union_all
from wtforms import (
    Form, SelectField, TextAreaField, PasswordField,
    StringField, IntegerField, validators)

import airflow
from airflow import configuration as conf, LoggingMixin, configuration
from airflow import models
from airflow import settings
from airflow import jobs
from airflow.api.common.experimental.mark_tasks import (set_dag_run_state_to_running,
                                                        set_dag_run_state_to_success,
                                                        set_dag_run_state_to_failed)
from airflow.exceptions import AirflowException
from airflow.models import BaseOperator, Connection, DagRun, errors, XCom
from airflow.operators.subdag_operator import SubDagOperator
from airflow.utils import timezone
from airflow.utils.dates import infer_time_unit, scale_time_units, parse_execution_date
from airflow.utils.db import create_session, provide_session
from airflow.utils.helpers import alchemy_to_dict, render_log_filename
from airflow.utils.net import get_hostname
from airflow.utils.state import State
from airflow.utils.timezone import datetime
from airflow.www import utils as wwwutils
from airflow.www.forms import (DateTimeForm, DateTimeWithNumRunsForm,
                               DateTimeWithNumRunsWithDagRunsForm)
from airflow.www.validators import GreaterEqualThan

QUERY_LIMIT = 100000
CHART_LIMIT = 200000

UTF8_READER = codecs.getreader('utf-8')

dagbag = models.DagBag(settings.DAGS_FOLDER)

# logout_user = airflow.login.logout_user

FILTER_BY_OWNER = False

PAGE_SIZE = conf.getint('webserver', 'page_size')

if conf.getboolean('webserver', 'FILTER_BY_OWNER'):
    # filter_by_owner if authentication is enabled and filter_by_owner is true
    FILTER_BY_OWNER = not current_app.config['LOGIN_DISABLED']


def dag_link(v, c, m, p):
    if m.dag_id is None:
        return Markup()

    kwargs = {'dag_id': m.dag_id}

    # This is called with various objects, TIs, (ORM) DAG - some have this,
    # some don't
    if hasattr(m, 'execution_date'):
        kwargs['execution_date'] = m.execution_date

    url = url_for('airflow.graph', **kwargs)
    return Markup(
        '<a href="{}">{}</a>').format(url, m.dag_id)


def log_url_formatter(v, c, m, p):
    url = url_for(
        'airflow.log',
        dag_id=m.dag_id,
        task_id=m.task_id,
        execution_date=m.execution_date.isoformat())
    return Markup(
        '<a href="{log_url}">'
        '    <span class="glyphicon glyphicon-book" aria-hidden="true">'
        '</span></a>').format(log_url=url)


def dag_run_link(v, c, m, p):
    url = url_for(
        'airflow.graph',
        dag_id=m.dag_id,
        run_id=m.run_id,
        execution_date=m.execution_date)
    title = m.run_id
    return Markup('<a href="{url}">{title}</a>').format(**locals())


def task_instance_link(v, c, m, p):
    url = url_for(
        'airflow.task',
        dag_id=m.dag_id,
        task_id=m.task_id,
        execution_date=m.execution_date.isoformat())
    url_root = url_for(
        'airflow.graph',
        dag_id=m.dag_id,
        root=m.task_id,
        execution_date=m.execution_date.isoformat())
    return Markup(
        """
        <span style="white-space: nowrap;">
        <a href="{url}">{m.task_id}</a>
        <a href="{url_root}" title="Filter on this task and upstream">
        <span class="glyphicon glyphicon-filter" style="margin-left: 0px;"
            aria-hidden="true"></span>
        </a>
        </span>
        """).format(**locals())


def state_token(state):
    color = State.color(state)
    return Markup(
        '<span class="label" style="background-color:{color};">'
        '{state}</span>').format(**locals())


def parse_datetime_f(value):
    if not isinstance(value, dt.datetime):
        return value

    return timezone.make_aware(value)


def state_f(v, c, m, p):
    return state_token(m.state)


def duration_f(v, c, m, p):
    if m.end_date and m.duration:
        return timedelta(seconds=m.duration)


def datetime_f(v, c, m, p):
    attr = getattr(m, p)
    dttm = attr.isoformat() if attr else ''
    if timezone.utcnow().isoformat()[:4] == dttm[:4]:
        dttm = dttm[5:]
    return Markup("<nobr>{}</nobr>").format(dttm)


def nobr_f(v, c, m, p):
    return Markup("<nobr>{}</nobr>").format(getattr(m, p))


def label_link(v, c, m, p):
    try:
        default_params = ast.literal_eval(m.default_params)
    except Exception:
        default_params = {}
    url = url_for(
        'airflow.chart', chart_id=m.id, iteration_no=m.iteration_no,
        **default_params)
    title = m.label
    return Markup("<a href='{url}'>{title}</a>").format(**locals())


def pool_link(v, c, m, p):
    title = m.pool

    url = url_for('taskinstance.index_view', flt1_pool_equals=m.pool)
    return Markup("<a href='{url}'>{title}</a>").format(**locals())


def pygment_html_render(s, lexer=lexers.TextLexer):
    return highlight(
        s,
        lexer(),
        HtmlFormatter(linenos=True),
    )


def render(obj, lexer):
    out = ""
    if isinstance(obj, basestring):
        out += pygment_html_render(obj, lexer)
    elif isinstance(obj, (tuple, list)):
        for i, s in enumerate(obj):
            out += "<div>List item #{}</div>".format(i)
            out += "<div>" + pygment_html_render(s, lexer) + "</div>"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out += '<div>Dict item "{}"</div>'.format(k)
            out += "<div>" + pygment_html_render(v, lexer) + "</div>"
    return out


def wrapped_markdown(s):
    return '<div class="rich_doc">' + markdown.markdown(s) + "</div>"


attr_renderer = {
    'bash_command': lambda x: render(x, lexers.BashLexer),
    'hql': lambda x: render(x, lexers.SqlLexer),
    'sql': lambda x: render(x, lexers.SqlLexer),
    'doc': lambda x: render(x, lexers.TextLexer),
    'doc_json': lambda x: render(x, lexers.JsonLexer),
    'doc_rst': lambda x: render(x, lexers.RstLexer),
    'doc_yaml': lambda x: render(x, lexers.YamlLexer),
    'doc_md': wrapped_markdown,
    'python_callable': lambda x: render(
        wwwutils.get_python_source(x),
        lexers.PythonLexer,
    ),
}


def data_profiling_required(f):
    """Decorator for views requiring data profiling access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if (
                current_app.config['LOGIN_DISABLED']
        ):
            return f(*args, **kwargs)
        else:
            flash("This page requires data profiling privileges", "error")
            return redirect(url_for('admin.index'))

    return decorated_function


def fused_slots(v, c, m, p):
    url = url_for(
        'taskinstance.index_view',
        flt1_pool_equals=m.pool,
        flt2_state_equals='running',
    )
    return Markup("<a href='{0}'>{1}</a>").format(url, m.used_slots())


def fqueued_slots(v, c, m, p):
    url = url_for(
        'taskinstance.index_view',
        flt1_pool_equals=m.pool,
        flt2_state_equals='queued',
        sort='1',
        desc='1'
    )
    return Markup("<a href='{0}'>{1}</a>").format(url, m.queued_slots())


def recurse_tasks(tasks, task_ids, dag_ids, task_id_to_dag):
    if isinstance(tasks, list):
        for task in tasks:
            recurse_tasks(task, task_ids, dag_ids, task_id_to_dag)
        return
    if isinstance(tasks, SubDagOperator):
        subtasks = tasks.subdag.tasks
        dag_ids.append(tasks.subdag.dag_id)
        for subtask in subtasks:
            if subtask.task_id not in task_ids:
                task_ids.append(subtask.task_id)
                task_id_to_dag[subtask.task_id] = tasks.subdag
        recurse_tasks(subtasks, task_ids, dag_ids, task_id_to_dag)
    if isinstance(tasks, BaseOperator):
        task_id_to_dag[tasks.task_id] = tasks.dag


def get_chart_height(dag):
    """
    TODO(aoen): See [AIRFLOW-1263] We use the number of tasks in the DAG as a heuristic to
    approximate the size of generated chart (otherwise the charts are tiny and unreadable
    when DAGs have a large number of tasks). Ideally nvd3 should allow for dynamic-height
    charts, that is charts that take up space based on the size of the components within.
    """
    return 600 + len(dag.tasks) * 10


def get_date_time_num_runs_dag_runs_form_data(request, session, dag):
    dttm = request.args.get('execution_date')
    if dttm:
        dttm = pendulum.parse(dttm)
    else:
        dttm = dag.latest_execution_date or timezone.utcnow()

    base_date = request.args.get('base_date')
    if base_date:
        base_date = timezone.parse(base_date)
    else:
        # The DateTimeField widget truncates milliseconds and would loose
        # the first dag run. Round to next second.
        base_date = (dttm + timedelta(seconds=1)).replace(microsecond=0)

    default_dag_run = conf.getint('webserver', 'default_dag_run_display_number')
    num_runs = request.args.get('num_runs')
    num_runs = int(num_runs) if num_runs else default_dag_run

    DR = models.DagRun
    drs = (
        session.query(DR)
        .filter(
            DR.dag_id == dag.dag_id,
            DR.execution_date <= base_date)
        .order_by(desc(DR.execution_date))
        .limit(num_runs)
        .all()
    )
    dr_choices = []
    dr_state = None
    for dr in drs:
        dr_choices.append((dr.execution_date.isoformat(), dr.run_id))
        if dttm == dr.execution_date:
            dr_state = dr.state

    # Happens if base_date was changed and the selected dag run is not in result
    if not dr_state and drs:
        dr = drs[0]
        dttm = dr.execution_date
        dr_state = dr.state

    return {
        'dttm': dttm,
        'base_date': base_date,
        'num_runs': num_runs,
        'execution_date': dttm.isoformat(),
        'dr_choices': dr_choices,
        'dr_state': dr_state,
    }


class AirflowViewMixin(object):
    def render(self, template, **kwargs):
        kwargs['scheduler_job'] = lazy_object_proxy.Proxy(jobs.SchedulerJob.most_recent_job)
        kwargs['macros'] = airflow.macros
        return super(AirflowViewMixin, self).render(template, **kwargs)


class HomeView(AirflowViewMixin, AdminIndexView):
    @expose("/")
    
    @provide_session
    def index(self, session=None):
        DM = models.DagModel

        # restrict the dags shown if filter_by_owner and current user is not superuser
        do_filter = FILTER_BY_OWNER 
        owner_mode = conf.get('webserver', 'OWNER_MODE').strip().lower()

        hide_paused_dags_by_default = conf.getboolean('webserver',
                                                      'hide_paused_dags_by_default')
        show_paused_arg = request.args.get('showPaused', 'None')

        def get_int_arg(value, default=0):
            try:
                return int(value)
            except ValueError:
                return default

        arg_current_page = request.args.get('page', '0')
        arg_search_query = request.args.get('search', None)

        dags_per_page = PAGE_SIZE
        current_page = get_int_arg(arg_current_page, default=0)

        if show_paused_arg.strip().lower() == 'false':
            hide_paused = True
        elif show_paused_arg.strip().lower() == 'true':
            hide_paused = False
        else:
            hide_paused = hide_paused_dags_by_default

        # read orm_dags from the db
        query = session.query(DM)


        query = query.filter(~DM.is_subdag, DM.is_active)
        

        # optionally filter out "paused" dags
        if hide_paused:
            query = query.filter(~DM.is_paused)

        if arg_search_query:
            query = query.filter(
                DM.dag_id.ilike('%' + arg_search_query + '%') |
                DM.owners.ilike('%' + arg_search_query + '%')
            )

        query = query.order_by(DM.dag_id)

        start = current_page * dags_per_page
        end = start + dags_per_page

        dags = query.offset(start).limit(dags_per_page).all()

        import_errors = session.query(errors.ImportError).all()
        for ie in import_errors:
            flash(
                "Broken DAG: [{ie.filename}] {ie.stacktrace}".format(ie=ie),
                "error")

        from airflow.plugins_manager import import_errors as plugin_import_errors
        for filename, stacktrace in plugin_import_errors.items():
            flash(
                "Broken plugin: [{filename}] {stacktrace}".format(
                    stacktrace=stacktrace,
                    filename=filename),
                "error")

        num_of_all_dags = query.count()
        num_of_pages = int(math.ceil(num_of_all_dags / float(dags_per_page)))

        auto_complete_data = set()
        for row in query.with_entities(DM.dag_id, DM.owners):
            auto_complete_data.add(row.dag_id)
            auto_complete_data.add(row.owners)

        return self.render(
            'airflow/dags.html',
            dags=dags,
            hide_paused=hide_paused,
            current_page=current_page,
            search_query=arg_search_query if arg_search_query else '',
            page_size=dags_per_page,
            num_of_pages=num_of_pages,
            num_dag_from=min(start + 1, num_of_all_dags),
            num_dag_to=min(end, num_of_all_dags),
            num_of_all_dags=num_of_all_dags,
            paging=wwwutils.generate_pages(current_page, num_of_pages,
                                           search=arg_search_query,
                                           showPaused=not hide_paused),
            auto_complete_data=auto_complete_data)


class QueryView(wwwutils.DataProfilingMixin, AirflowViewMixin, BaseView):
    @expose('/', methods=['POST', 'GET'])
    @wwwutils.gzipped
    @provide_session
    def query(self, session=None):
        dbs = session.query(Connection).order_by(Connection.conn_id).all()
        session.expunge_all()
        db_choices = []
        for db in dbs:
            try:
                if db.get_hook():
                    db_choices.append((db.conn_id, db.conn_id))
            except Exception:
                pass
        conn_id_str = request.form.get('conn_id')
        csv = request.form.get('csv') == "true"
        sql = request.form.get('sql')

        class QueryForm(Form):
            conn_id = SelectField("Layout", choices=db_choices)
            sql = TextAreaField("SQL", widget=wwwutils.AceEditorWidget())

        data = {
            'conn_id': conn_id_str,
            'sql': sql,
        }
        results = None
        has_data = False
        error = False
        if conn_id_str and request.method == 'POST':
            db = [db for db in dbs if db.conn_id == conn_id_str][0]
            try:
                hook = db.get_hook()
                df = hook.get_pandas_df(wwwutils.limit_sql(sql, QUERY_LIMIT, conn_type=db.conn_type))
                # df = hook.get_pandas_df(sql)
                has_data = len(df) > 0
                df = df.fillna('')
                results = df.to_html(
                    classes=[
                        'table', 'table-bordered', 'table-striped', 'no-wrap'],
                    index=False,
                    na_rep='',
                ) if has_data else ''
            except Exception as e:
                flash(str(e), 'error')
                error = True

        if has_data and len(df) == QUERY_LIMIT:
            flash(
                "Query output truncated at " + str(QUERY_LIMIT) +
                " rows", 'info')

        if not has_data and error:
            flash('No data', 'error')

        if csv:
            return Response(
                response=df.to_csv(index=False),
                status=200,
                mimetype="application/text")

        form = QueryForm(request.form, data=data)
        session.commit()
        return self.render(
            'airflow/query.html', form=form,
            title="Ad Hoc Query",
            results=results or '',
            has_data=has_data)


