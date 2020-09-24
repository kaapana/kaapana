from kubernetes import client
import uuid

class Ingress():
    """
    Represents a kubernetes ingress.
    :param path: the path name
    :type path: str
    :param name: the ingress name
    :type name: str
    :param namespace: the namespace for the ingress
    :type envs: str
    :param annotations: A dict containing a annotations
    :type annotations: dict
    """

    def __init__(
            self,
            path,
            name,
            service_name,
            service_port,
            kind='Ingress',
            namespace='default',
            annotations=None,
            labels=None,
    ):
        self.name = name + str(uuid.uuid1())[:8]
        self.namespace = namespace
        self.annotations = annotations or {}

        self.service_name = service_name
        self.service_port = service_port
        self.path = path
        self.kind = kind
        self.labels = labels or {}

    def get_kube_object(self):
    
        metadata = client.V1ObjectMeta()
        metadata.name =  self.name
        metadata.namespace = self.namespace

        metadata.annotations = self.annotations
        metadata.labels = self.labels
        backend = client.NetworkingV1beta1IngressBackend(service_name=self.service_name, service_port=self.service_port)
        pathList = [
            client.NetworkingV1beta1HTTPIngressPath(path=self.path, backend=backend)
        ]
        httpIngressRule = client.NetworkingV1beta1HTTPIngressRuleValue(paths=pathList)

        specList = [
           client.NetworkingV1beta1IngressRule(http=httpIngressRule)
        ]

        spec = client.NetworkingV1beta1IngressSpec(rules=specList)

        ingress = client.NetworkingV1beta1Ingress(metadata=metadata, spec=spec)  

        return ingress