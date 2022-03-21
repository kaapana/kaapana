from threading import Timer


from fastapi import Depends


from app import crud
from app import schemas
from app.dependencies import get_db
from app.utils import get_dag_list, get_dataset_list

def execute_scheduled_jobs():
    print('checking')
    # with next(get_db()) as db:
    #     db_client_kaapana = crud.get_kaapana_instance(db, remote=False)
    #     for job in db_client_kaapana.jobs:
    #         print(job)
    
class RepeatedTimer(object):
    '''Copied from services/kaapana-core/kube-helm/docker/files/app/repeat_timer.py'''
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

    def set_interval(self,interval):
        if self.is_running:
            self.stop()

        self.interval = interval
        self.start()
