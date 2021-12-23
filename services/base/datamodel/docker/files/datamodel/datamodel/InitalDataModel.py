# import flask
# import networkx as nx
# import logging
# # import-request:
# # {
# #     "files": [
# #         "file://ctp-volume/import/import-folder",
# #         "file://ctp-volume/import/import-folder/asdfas.dcm"
# #     ]
# #     "options": {
# #         "store": true,
# #         "aetitle_ownership": true,
# #         "permission": group3
# #     }
# # }
# #
# # Import Process
# # 1. User calls api endpoint with import-request object
# # 2. Datamodel backend makes file localy available (on local volume, download it)
# # 3. The file is indexed by a data importer
# # 4. The file is stored (PACS, MINIO)
# # 5. commit changes to datamodel
# #
# # Data node lifecycle (data node is a node containing a reference to data)
# # 1. indexed
# # 2. localy-stored
#
#
# app = flask.Flask(__name__)
#
# class Datamodel:
#     def __init__(self):
#         self.G = nx.Graph()
#
#         self.G.add_node("kaapana-root", {"version": "0.0.1"})
#
#         self.G.add_node("data")
#         self.G.add_node("kaapana-root", "data")
#
#     def commit_import_graph(self, D):
#         #TODO merge conflicts
#         self.G = nx.union(self.G, D)
#
#
# class DataImporter:
#     def __init__(self):
#         self.log = logging.getLogger(__name__)
#
#     def can_import(path):
#         return False
#
#     def import_data(self, datamodel: Datamodel, files, options = None):
#         pass
#
# class DicomDataImporter(DataImporter):
#
#
#     def can_import(self, path):
#         from pydicom import dcmread
#         from pydicom.errors import InvalidDicomError
#         try:
#             self.ds = dcmread(path)
#         except InvalidDicomError:
#             return False
#         return True
#
#     def import_data(self, datamodel: Datamodel, files, options = None):
#         if not datamodel.G.has_edge("data", "dicom"):
#             datamodel.G.add_edge("data", "dicom")
#
#         for file in files:
#             # Step 1 - Make file Acessible
#             ds = dcmread(file)
#
#             # Step 2 - Indexing
#             patient_uid = f"dicom://{ds.PatientID.asdf}"
#             study_uid = f"dicom://{file.asdf}"
#             series_uid = f"dicom://{file.asdf}"
#             instance_uid = f"dicom://{file.asdf}"
#
#             D = nx.Graph()
#             D.add_node(patient_uid)
#             D.add_edge("dicom", patient_uid)
#             D.add_node(study_uid)
#             D.add_edge(patient_uid, study_uid)
#             D.add_node(series_uid, {"modality": ds.Modality})
#             D.add_edge(study_uid, series_uid)
#             D.add_node(instance_uid)
#             D.add_edge(series_uid, instance_uid)
#
#             datamodel.commit_import_graph(D)
#             if options.aetitle_ownership:
#                 if G.has_node(aetitle):
#                     G.add_node(aetitle)
#                     G.add_edge("groups", aetitle)
#                 G.add_edge(aetitle, patient_uid, {""})
#                 # G.add_edge(aetitle, study_uid, {"revoke"})
#             # kaapana -> users -> Schmitt -> cohorts -> query
#             #                             -> list -> uid
#             #                             -> permisions -> uid (read)
#             #         -> groups -> list (uids) user
#             #                   -> list (uids) files
#             #         -> data
#             #
#             # dataX --> group -> user
#             # user -> XXXX -> dataX ("read")
#             # user -> XXXX -> dataX ("write")
#             # user -> Schmitt -> Patient -> Study-> dataX ("revoke")
#             # user -> Schmitt -> Patient -> Study-> Instance -> dataX ("read")
#
#             # Permission Model: option A
#             PermissionGraph.add_edge(aetitle, patient_node, {"read": True})
#             return [n for n in result if PermisionGraph.has_edge(request.user, n)]
#             # Permission Model: option B
#             patient_node.data["owner"] = aetitle
#             #multiacess handle option
#             #patient_node.data["access"].append(aetitle)
#             if options.aetitle_ownership:
#                 aetitle
#
#             # Step 3 - Store actual data
#
#
# class RawImporter(DataImporter):
#     def can_import(path):
#         return True
#
#     def import_data(self, datamodel: Datamodel, files, options = None):
#         G = datamodel.G
#
#         nx.union(datamodel.G, D)
#         datamodel.G.add_edge("dicom-data", "patient")
#         for file in files:
#             path_componentes = file.path.split("/")
#             uid = f"sha-1://{file.sha1}"
#             node = G.add_node(uid, {"name": file.name})
#
#
#
#     def generate_uid(self, file)
#
# class MultiImporter(DataImporter):
#     def __init__(self):
#         self.importers = [
#             DicomDataImporter(),
#             RawImporter()
#         ]
#
#     def can_import(self, path):
#         for i in self.importers:
#             if i.can_import(path):
#                 return True
#         return False
#
#     def import_data(self, datamodel: Datamodel, files, options = None):
#         # expects homogenous files (e.g. all dicom)
#         for i in self.importers:
#             if i.can_import(files[0]):
#                 i.import_data(datamodel, files, options)
#                 return
#         raise Exception("No importer found")
#
#
#
# def process_import(files, options=None, importer=MultiImporter()):
#     for x in files:
#         if x.isdir():
#         else:
#
#
# @app.route('/datamodel_map', methods = ['GET'])
# def get_datamodel_map():
#     from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
#     from matplotlib.figure import Figure
#     import io
#
#     fig=Figure()
#     nx.draw(datamodel.G)
#     output = io.BytesIO()
#     FigureCanvas(fig).print_png(output)
#     return flask.Response(output.getvalue(), mimetype="image/png")