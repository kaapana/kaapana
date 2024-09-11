from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


def get_dcmweb_helper(
    dcmweb_endpoint=None,
    service_account_info=None,
):
    if dcmweb_endpoint:
        try:
            # Check if external_pacs extension was installed
            from external_pacs.HelperDcmWebGcloud import HelperDcmWebGcloud
            from external_pacs.utils import get_k8s_secret, hash_secret_name

            secret_name = hash_secret_name(name=dcmweb_endpoint)
            if not service_account_info:
                service_account_info = get_k8s_secret(secret_name)
            if not service_account_info:
                raise FileNotFoundError(f"Cannot retrieve secret for {dcmweb_endpoint}")

            if "google" in dcmweb_endpoint and service_account_info:
                return HelperDcmWebGcloud(
                    dcmweb_endpoint=dcmweb_endpoint,
                    service_account_info=service_account_info,
                )
            else:
                logger.error(f"Unsupported dcmweb_endpoint: {dcmweb_endpoint}")
                exit(1)

        except ModuleNotFoundError:
            logger.error(
                "There is no external helper installed - see extensions external-pacs"
            )
            exit(1)

        except Exception:
            logger.error(f"Unknown dcmweb_endpoint: {dcmweb_endpoint}")
            exit(1)
    else:
        return HelperDcmWeb()
