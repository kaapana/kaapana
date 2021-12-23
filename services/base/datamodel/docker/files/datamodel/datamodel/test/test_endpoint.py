
from flask import Flask
from datamodel.database.base import db_session
from datamodel.Datamodel import KaapanaDatamodel
from datamodel.DatamodelB import KaapanaDatamodelB
import os
app = Flask("test_endpoint")
app.debug = True

# app.add_url_rule(
#     '/graphql',
#     view_func=GraphQLView.as_view(
#         'graphql',
#         schema=schema,
#         graphiql=True # for having the GraphiQL interface
#     )
# )

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

if __name__ == '__main__':
    #init_db()
    DM = KaapanaDatamodelB()
    DM.setup_db(app)

    pathToFolder ="/home/hanno/project/kaapana-internal-datamodel/services/base/datamodel/datamodel/test/images/"
    files = []
    for dirpath, dirnames, fileNames in os.walk(pathToFolder):
        for fileName in fileNames:
            if fileName.endswith('.dcm'):
                path = os.path.join(dirpath, fileName)
                files.append(path)
    storage_path = { "storage_path": "test_path"}
    content= {"files": files, "options": storage_path}
    DM.import_dicom(content)
    # import again as raw, the same files
    # folder
    folder = None
    content = {"files": files, "options": folder}
    DM.import_raw(content)


    app.run()
