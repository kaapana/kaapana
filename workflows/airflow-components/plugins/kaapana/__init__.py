# # This is the class you derive to create a plugin
# from airflow.plugins_manager import AirflowPlugin
#
# from flask import Blueprint
# from flask_admin import BaseView, expose
# from flask_admin.base import MenuLink
# from flask_appbuilder import BaseView as AppBuilderBaseView
#
# # Importing base classes that we need to derive
# from airflow.hooks.base_hook import BaseHook
# from airflow.models import BaseOperator, Variable
# from airflow.sensors.base_sensor_operator import BaseSensorOperator
# from airflow.executors.base_executor import BaseExecutor
# from kaapana.blueprints.kaapana_api import kaapanaApi
# from kaapana import operators
#
# class PluginHook(BaseHook):
#     pass
#
# # Will show up under airflow.operators.test_plugin.PluginOperator
#
#
# class PluginOperator(BaseOperator):
#     pass
#
#
# # Will show up under airflow.sensors.test_plugin.PluginSensorOperator
# class PluginSensorOperator(BaseSensorOperator):
#     pass
#
#
# # Will show up under airflow.executors.test_plugin.PluginExecutor
# class PluginExecutor(BaseExecutor):
#     pass
#
# # Will show up under airflow.macros.test_plugin.plugin_macro
#
#
# def plugin_macro():
#     pass
#
# # Creating a flask admin BaseView
#
#
# class TestView(BaseView):
#     @expose('/')
#     def test(self):
#         # in this example, put your test_plugin/test.html template at airflow/plugins/templates/test_plugin/test.html
#         return self.render("kaapana/home.html", content="Hello galaxy!")
#
#
# # v = TestView(category="JIP", name="Jip Dags")
# # dags_view=blueprints.JipDags(category="JIP", name="Jip Dags2")
#
# # Creating a flask appbuilder BaseView
# # class TestAppBuilderBaseView(AppBuilderBaseView):
# #     default_view = "test"
#
# #     @expose("/")
# #     def test(self):
# #         return self.render("kaapana/home.html", content="Hello galaxy!")
#
#
# # v_appbuilder_view = TestAppBuilderBaseView()
# # v_appbuilder_package = {"name": "Test View2",
# #                         "category": "Jip Plugin",
# #                         "view": v_appbuilder_view}
#
#
# # jip_dags_appbuilder_view = blueprints.JipDags()
# # jip_dags_appbuilder_package = {"name": "JIP DAGS",
# #                         "category": "Jip Plugin",
# #                         "view": jip_dags_appbuilder_view}
#
# # Creating a flask appbuilder Menu Item
# appbuilder_mitem = {"name": "Google",
#                     "category": "Search",
#                     "category_icon": "fa-th",
#                     "href": "https://www.google.com"}
#
# jip_operators = [
#     PluginOperator,
#     # operators.local_operator_get_ref_series_from_pacs,
#     # operators.local_operator_jip_slack,
#     # operators.local_operator_json2meta,
#     # operators.local_operator_workflow_cleaner,
#     # operators.local_operator_dag_trigger,
#     # operators.local_operator_files2minio,
#     # operators.local_operator_combine_seg_dcm,
#     # operators.local_operator_getIidUrl,
#     # operators.operator_brain_extraction,
#     # operators.operator_dcm2nifti,
#     # operators.operator_dcm2nrrd,
#     # operators.operator_dcm_seg2nrrd,
#     # operators.operator_dcm_sendDimse,
#     # operators.operator_dcm_sendWeb,
#     # operators.operator_json2dcmSR,
#     # operators.operator_lung_seg,
#     # operators.operator_nrrd2dcmseg,
#     # operators.operator_organ_seg,
#     # operators.operator_radiomics
# ]
#
# # Creating a flask blueprint to intergrate the templates and static folder
# # bp = Blueprint(
# #     "kaapana", __name__,
# #     # registers airflow/plugins/templates as a Jinja template folder
# #     template_folder='templates',
# #     static_folder='static',
# #     static_url_path='/static/kaapana')
#
# kaapana_blueprints = [
#     # bp,
#     kaapanaApi
# ]
#
#
# # base = MenuLink(
# #     category='JIP',
# #     name='BASE',
# #     url='/')
#
# # meta = MenuLink(
# #     category='JIP',
# #     name='META',
# #     url='/meta')
#
# # pacs = MenuLink(
# #     category='JIP',
# #     name='PACS',
# #     url='/pacs')
#
#
# # Defining the plugin class
# class AirflowTestPlugin(AirflowPlugin):
#     name = "kaapanajip_plugin"
#     operators = jip_operators
#     sensors = [PluginSensorOperator]
#     hooks = [PluginHook]
#     executors = [PluginExecutor]
#     macros = [plugin_macro]
#     admin_views = []  # ,dags_view]
#     flask_blueprints = kaapana_blueprints
#     menu_links = []  # [base, meta, pacs]
#     appbuilder_views = []  # [v_appbuilder_package,jip_dags_appbuilder_package]
#     appbuilder_menu_items = [appbuilder_mitem]
