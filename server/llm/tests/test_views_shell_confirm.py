import json

from django.test import Client


def test_shell_confirm_ejecuta_comando_permitido(client: Client) -> None:
    response = client.post(
        "/api/shell/confirm",
        data=json.dumps({"command": "echo hola"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body["executed"] is True
    assert "hola" in body["stdout"]


def test_shell_confirm_bloquea_comando_peligroso(client: Client) -> None:
    response = client.post(
        "/api/shell/confirm",
        data=json.dumps({"command": "rm -rf /"}),
        content_type="application/json",
    )

    body = json.loads(response.content)
    assert body["executed"] is False
    assert body["blocked_reason"] is not None
