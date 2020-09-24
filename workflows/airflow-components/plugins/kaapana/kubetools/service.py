from kubernetes import client
import uuid

class Service():
    """
    Represents a kubernetes service.
    :param name: the ingress name
    :type name: str
    :param namespace: the namespace for the ingress
    :type envs: str
    """

    def __init__(
            self,
            name,
            port,
            selector=None,
            kind='Service',
            namespace='default',
            labels=None,
    ):
        self.name = name + str(uuid.uuid1())[:8]
        self.namespace = namespace
        self.service_port = name[-10:]+"-http"
        self.port = port
        self.kind = kind
        self.selector = selector
        self.labels = labels or {}

    def get_kube_object(self):
    
        metadata = client.V1ObjectMeta()
        metadata.name =  self.name
        metadata.namespace = self.namespace
        metadata.labels= self.labels

        ports = [client.V1ServicePort(protocol="TCP", port=self.port, name=self.service_port)]

        spec = client.V1ServiceSpec(type="ClusterIP", selector=self.selector, ports=ports)

        service = client.V1Service(api_version="v1", kind="Service", spec=spec, metadata=metadata) 

        return service