import app.api as api
import app.ingress_source as ingress_source
import pytest
from app.main import app as fastapi_app
from app.menu import IngressInfo, _is_platform_relative, build_menu
from fastapi.testclient import TestClient


def ing(
    ingress_name: str,
    namespace: str = "services",
    first_path: str | None = None,
    **ui: str,
) -> IngressInfo:
    """IngressInfo with kaapana.ai/ui.* annotations from kwargs (underscores -> dashes)."""
    annotations = {
        f"kaapana.ai/ui.{key.replace('_', '-')}": value for key, value in ui.items()
    }
    return IngressInfo(
        namespace=namespace,
        name=ingress_name,
        annotations=annotations,
        first_path=first_path,
    )


def items(*ingresses: IngressInfo) -> list:
    return build_menu(list(ingresses)).items


def test_ingress_without_ui_name_is_excluded() -> None:
    assert (
        items(
            IngressInfo(
                "services", "plain", {"kaapana.ai/type": "application"}, "/plain"
            )
        )
        == []
    )


def test_entry_defaults_and_path_fallback_to_rule_path() -> None:
    (entry,) = items(ing("my-app", first_path="/my-app", name="My App"))
    assert entry.type == "entry"
    assert entry.id == "my-app"
    assert entry.label == "My App"
    assert entry.icon == ""
    assert entry.path == "/my-app"
    assert entry.target == "iframe"
    assert entry.default is False
    assert entry.order == 1000


def test_explicit_ui_path_wins_over_rule_path() -> None:
    (entry,) = items(ing("flow", first_path="/flow", name="Airflow", path="/flow/home"))
    assert entry.path == "/flow/home"


def test_invalid_ui_path_falls_back_to_rule_path() -> None:
    (entry,) = items(ing("flow", first_path="/flow", name="Airflow", path="no-slash"))
    assert entry.path == "/flow"


def test_no_valid_path_skips_entry() -> None:
    assert items(ing("broken", first_path=None, name="Broken")) == []


def test_empty_name_skips_entry() -> None:
    assert items(ing("empty", first_path="/x", name="   ")) == []


def test_malformed_order_defaults_and_entry_kept() -> None:
    (entry,) = items(ing("a", first_path="/a", name="A", order="ten"))
    assert entry.order == 1000


def test_unknown_ui_annotation_is_ignored() -> None:
    (entry,) = items(ing("a", first_path="/a", name="A", nmae="typo"))
    assert entry.label == "A"


def test_unknown_target_falls_back_to_iframe() -> None:
    (entry,) = items(ing("a", first_path="/a", name="A", target="popup"))
    assert entry.target == "iframe"


def test_project_annotation_parsed() -> None:
    (entry,) = items(ing("b", first_path="/b", name="B", project="path"))
    assert entry.project == "path"
    # "live" was removed with the localStorage-based project contract.
    (entry,) = items(ing("a", first_path="/a", name="A", project="live"))
    assert entry.project == "none"


def test_project_defaults_to_none_and_rejects_unknown_values() -> None:
    (entry,) = items(ing("a", first_path="/a", name="A"))
    assert entry.project == "none"
    (entry,) = items(ing("b", first_path="/b", name="B", project="bogus"))
    assert entry.project == "none"


def test_badge_path_parsed_and_defaults_empty() -> None:
    (entry,) = items(
        ing("a", first_path="/a", name="A", badge_path="/kube-helm-api/x-count")
    )
    assert entry.badgePath == "/kube-helm-api/x-count"
    (entry,) = items(ing("b", first_path="/b", name="B"))
    assert entry.badgePath == ""


def test_badge_path_without_leading_slash_ignored() -> None:
    (entry,) = items(ing("a", first_path="/a", name="A", badge_path="no-slash"))
    assert entry.badgePath == ""


def test_protocol_relative_badge_path_ignored() -> None:
    # "//host/x" passes a bare startswith("/") check but the shell would poll
    # another origin every 15s, leaking each viewer to it.
    (entry,) = items(ing("a", first_path="/a", name="A", badge_path="//evil.com/count"))
    assert entry.badgePath == ""


def test_protocol_relative_ui_path_falls_back_to_the_rule_path() -> None:
    (entry,) = items(ing("a", first_path="/a", name="A", path="//evil.com/"))
    assert entry.path == "/a"


def test_protocol_relative_rule_path_skips_the_entry() -> None:
    assert items(ing("a", first_path="//evil.com/", name="A")) == []


def test_is_platform_relative_accepts_platform_paths() -> None:
    assert _is_platform_relative("/foo/bar")
    assert _is_platform_relative("/")


def test_is_platform_relative_rejects_protocol_relative() -> None:
    assert not _is_platform_relative("//host")
    assert not _is_platform_relative("//evil.com/x")


def test_is_platform_relative_rejects_backslash_authority() -> None:
    # For special schemes the WHATWG URL parser reads "\" as "/", so "/\host"
    # resolves to https://host — same off-origin escape as "//host".
    assert not _is_platform_relative("/\\evil.com/x")


def test_is_platform_relative_rejects_control_char_smuggled_authority() -> None:
    # The URL parser strips ASCII tab/newline/CR first, so these collapse to a
    # protocol-relative form the naive startswith("//") check would have missed.
    assert not _is_platform_relative("/\t/evil.com/x")
    assert not _is_platform_relative("/\t//host")
    assert not _is_platform_relative("/\n/evil.com")
    assert not _is_platform_relative("/\r/evil.com")


def test_ui_path_is_stripped() -> None:
    (entry,) = items(ing("a", first_path="/a", name="A", path="  /valid/path  "))
    assert entry.path == "/valid/path"


def test_whitespace_wrapped_protocol_relative_ui_path_falls_back() -> None:
    (entry,) = items(ing("a", first_path="/a", name="A", path="  //evil.com/  "))
    assert entry.path == "/a"


def test_dev_links_parsed_and_default_empty() -> None:
    (entry,) = items(
        ing(
            "a",
            first_path="/a",
            name="A",
            dev_links="Kaapana Backend=/kaapana-backend/docs, Kube-Helm API=/kube-helm-api/docs",
        )
    )
    assert [(link.label, link.path) for link in entry.devLinks] == [
        ("Kaapana Backend", "/kaapana-backend/docs"),
        ("Kube-Helm API", "/kube-helm-api/docs"),
    ]
    (entry,) = items(ing("b", first_path="/b", name="B"))
    assert entry.devLinks == []


def test_malformed_dev_link_pair_skipped_and_entry_kept() -> None:
    (entry,) = items(
        ing(
            "a",
            first_path="/a",
            name="A",
            dev_links="no-separator,Missing Path=,=/orphan,Relative=kaapana-backend/docs,"
            "Good=/data-api/docs",
        )
    )
    assert entry.label == "A"
    assert [link.path for link in entry.devLinks] == ["/data-api/docs"]


def test_protocol_relative_dev_link_skipped() -> None:
    # "//evil.com/docs" starts with "/" but resolves off-platform.
    (entry,) = items(
        ing(
            "a",
            first_path="/a",
            name="A",
            dev_links="Evil=//evil.com/docs,Good=/data-api/docs",
        )
    )
    assert [link.path for link in entry.devLinks] == ["/data-api/docs"]


def test_empty_dev_links_annotation_is_silent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level("WARNING"):
        (entry,) = items(ing("a", first_path="/a", name="A", dev_links="  "))
    assert entry.devLinks == []
    assert caplog.records == []


def test_ui_id_overrides_slug() -> None:
    (entry,) = items(
        ing("docs", first_path="/docs", name="Documentation", id="Documentation")
    )
    assert entry.id == "Documentation"


def test_id_slugified_from_name() -> None:
    (entry,) = items(ing("upload", first_path="/data-upload", name="  Data Upload! "))
    assert entry.id == "data-upload"


def test_duplicate_section_id_keeps_smallest_namespace_name() -> None:
    first = ing("a-app", first_path="/a", name="Datasets", section="workflows")
    second = ing("b-app", first_path="/b", name="Datasets", section="workflows")
    (section,) = items(second, first)
    (entry,) = section.entries
    assert entry.path == "/a"


def test_same_id_in_different_sections_is_no_duplicate() -> None:
    result = items(
        ing("a", first_path="/a", name="Datasets", section="workflows"),
        ing("b", first_path="/b", name="Datasets", section="store"),
    )
    assert len(result) == 2


def test_section_grouping_vs_top_level() -> None:
    result = items(
        ing("home", first_path="/home", name="Home"),
        ing("datasets", first_path="/datasets", name="Datasets", section="workflows"),
    )
    types = {item.type for item in result}
    assert types == {"entry", "section"}
    (section,) = [item for item in result if item.type == "section"]
    assert section.id == "workflows"
    assert [e.label for e in section.entries] == ["Datasets"]


def test_section_metadata_merge_is_order_independent() -> None:
    anchor = ing(
        "a-anchor",
        first_path="/a",
        name="A",
        section="store",
        section_label="Store",
        section_order="20",
    )
    other = ing(
        "z-other",
        first_path="/z",
        name="Z",
        section="store",
        section_label="Shop",
        section_icon="mdi-store",
        section_order="5",
    )
    for permutation in ([anchor, other], [other, anchor]):
        (section,) = items(*permutation)
        # per-field: smallest (namespace, name) that set it non-empty
        assert section.label == "Store"
        assert section.icon == "mdi-store"
        # numeric minimum over all declared values
        assert section.order == 5


def test_section_label_defaults_to_capitalized_id() -> None:
    (section,) = items(ing("a", first_path="/a", name="A", section="workflows"))
    assert section.label == "Workflows"
    assert section.icon == ""
    assert section.order == 1000


def test_malformed_section_order_ignored_in_minimum() -> None:
    (section,) = items(
        ing("a", first_path="/a", name="A", section="s", section_order="soon"),
        ing("b", first_path="/b", name="B", section="s", section_order="7"),
    )
    assert section.order == 7


def test_sorting_interleaves_sections_and_top_level_by_order_then_label() -> None:
    result = items(
        ing("ext", first_path="/extensions", name="Extensions", order="50"),
        ing("home", first_path="/home", name="Home", order="0"),
        ing(
            "ds",
            first_path="/datasets",
            name="Datasets",
            section="workflows",
            section_order="10",
            order="20",
        ),
        ing(
            "up",
            first_path="/data-upload",
            name="Data Upload",
            section="workflows",
            order="10",
        ),
    )
    assert [(item.type, item.label) for item in result] == [
        ("entry", "Home"),
        ("section", "Workflows"),
        ("entry", "Extensions"),
    ]
    assert [e.label for e in result[1].entries] == ["Data Upload", "Datasets"]


def test_duplicate_default_single_winner() -> None:
    result = items(
        ing("b-home", first_path="/b", name="B Home", default="true"),
        ing("a-home", first_path="/a", name="A Home", default="true"),
    )
    assert [(e.label, e.default) for e in result] == [
        ("A Home", True),
        ("B Home", False),
    ]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(api, "_menu", None)
    monkeypatch.setattr(api, "_fetched_at", 0.0)
    return TestClient(fastapi_app)


def test_menu_within_the_ttl_is_served_from_cache(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    async def counted() -> list[IngressInfo]:
        nonlocal calls
        calls += 1
        return [ing("home", first_path="/home", name="Home")]

    monkeypatch.setattr(ingress_source, "list_ingresses", counted)
    first = client.get("/menu")
    second = client.get("/menu")
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    # the second request is within CACHE_TTL_SECONDS, so it must not hit k8s
    assert calls == 1


def test_menu_endpoint_503_before_first_fetch_then_stale_serve(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> list[IngressInfo]:
        raise RuntimeError("api server down")

    async def succeed() -> list[IngressInfo]:
        return [ing("home", first_path="/home", name="Home")]

    monkeypatch.setattr(ingress_source, "list_ingresses", fail)
    assert client.get("/menu").status_code == 503

    monkeypatch.setattr(ingress_source, "list_ingresses", succeed)
    response = client.get("/menu")
    assert response.status_code == 200
    assert [item["label"] for item in response.json()["items"]] == ["Home"]

    # expire the cache, break the k8s API again: stale menu is served
    monkeypatch.setattr(ingress_source, "list_ingresses", fail)
    monkeypatch.setattr(api, "_fetched_at", api._fetched_at - 10_000)
    response = client.get("/menu")
    assert response.status_code == 200
    assert [item["label"] for item in response.json()["items"]] == ["Home"]
