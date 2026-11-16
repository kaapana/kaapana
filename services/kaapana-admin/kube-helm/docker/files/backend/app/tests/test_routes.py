"""Sends untrusted values through the real middleware and router."""


def test_complete_active_application_runs_no_injected_command(client, fake_cli, marker):
    payload = f"x; touch {marker}; #"

    response = client.post("/complete-active-application", json={"release_name": payload})

    assert response.status_code == 500
    (call,) = fake_cli.calls()
    assert f"--filter={payload}" in call
    assert not marker.exists()


def test_view_chart_status_passes_release_name_as_one_argument(client, fake_cli):
    response = client.get("/view-chart-status", params={"release_name": "demo --all"})

    assert response.status_code == 404
    assert fake_cli.calls() == [["-n", "default", "status", "-o", "yaml", "demo --all"]]
