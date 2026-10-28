"""Where DICOM comes from: the project's metadata index (OpenSearch) and DICOMweb (dicom-web-filter)."""

from pathlib import Path

from kaapana_nnunet.dicom import ConversionError

STUDY = "0020000D StudyInstanceUID_keyword"
SERIES = "0020000E SeriesInstanceUID_keyword"
MODALITY = "00080060 Modality_keyword"


class Metadata:
    """Series metadata of the project from the Kaapana metadata index."""

    def __init__(self, index: str):
        from kaapana_client.helper.HelperOpensearch import HelperOpensearch

        self.client = HelperOpensearch().os_client
        self.index = index

    def series(self, uids: list[str]) -> dict[str, dict]:
        out = {}
        for start in range(0, len(uids), 500):
            chunk = uids[start : start + 500]
            res = self.client.search(index=self.index, body={"query": {"ids": {"values": chunk}}, "size": len(chunk)})
            out.update({hit["_id"]: hit["_source"] for hit in res["hits"]["hits"]})
        return out

    def study_series(self, study_uid: str) -> list[dict]:
        res = self.client.search(
            index=self.index, body={"query": {"term": {f"{STUDY}.keyword": study_uid}}, "size": 1000}
        )
        return [hit["_source"] for hit in res["hits"]["hits"]]


def downloader(dicom_dir: Path):
    """download(series_uid, study_uid) -> local folder with the series (downloaded once)."""
    from kaapana_client.helper.HelperDcmWeb import HelperDcmWeb

    dcmweb = HelperDcmWeb()

    def download(uid: str, study_uid: str) -> Path:
        target = dicom_dir / uid
        if not target.is_dir() or not any(target.iterdir()):
            if not dcmweb.download_series(study_uid=study_uid, series_uid=uid, target_dir=str(target)):
                raise ConversionError(f"download of series {uid} failed")
        return target

    return download
