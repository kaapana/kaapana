class FederatedException(Exception):
    pass


class FederatedJobTimeoutException(FederatedException):
    """
    A federated job did not finish or fail within the given timeframe
    """

    def __init__(self, *args):
        message = "There are lacking updates, please check what is going on!"
        super().__init__(message, *args)


class FederatedJobFaildException(FederatedException):
    def __init__(self, instance_name: str, job_id: int):
        message = "A client job failed, interrupting, you can use the recovery_conf to continue your training, if there is an easy fix!"
        super().__init__(message, instance_name, job_id)
