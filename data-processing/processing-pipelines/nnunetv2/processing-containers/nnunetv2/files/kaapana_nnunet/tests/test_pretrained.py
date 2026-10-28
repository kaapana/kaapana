import pytest
from kaapana_nnunet import layout, pretrained
from kaapana_nnunet.store import NotPublished


class NoStore:
    def fetch(self, prefix, local_dir):
        raise NotPublished(prefix)


@pytest.fixture
def pod(tmp_path, monkeypatch):
    monkeypatch.setenv("NNUNET_POD_ROOT", str(tmp_path / "pod"))
    (tmp_path / "pod" / "pretrained").mkdir(parents=True)
    bundled = tmp_path / "bundled" / "MIC-DKFZ_nnFoundationCNN"
    bundled.mkdir(parents=True)
    for f in pretrained.REQUIRED_FILES:
        (bundled / f).write_text("x")
    monkeypatch.setenv("NNUNET_BUNDLED_PRETRAINED", str(tmp_path / "bundled"))
    return tmp_path


def test_bundled_checkpoint_keeps_the_pod_path(pod):
    checkpoint = pretrained.fetch(NoStore(), "nnFoundationCNN")
    # nnU-Net writes this path into the plans, so it must stay below /nnunet/pretrained
    assert checkpoint == layout.pod_dir("pretrained") / "MIC-DKFZ_nnFoundationCNN" / "checkpoint_final.pth"
    assert checkpoint.read_text() == "x"
    # train finds it again from the adapted plans, also when the link already exists
    pretrained.fetch_for_plans(NoStore(), {"pretrain_info": {"checkpoint_path": str(checkpoint)}})


def test_missing_checkpoint_explains_upload(pod):
    with pytest.raises(pretrained.PretrainedError, match="nnunetv2-refresh"):
        pretrained.fetch(NoStore(), "myOwnModel")
