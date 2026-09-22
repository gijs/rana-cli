"""Thin authenticated HTTP client for the Rana API.

Doesn't hardcode a wrapper per endpoint; `request()` takes any path (with
`{tenant_id}` filled in automatically) and handles auth + a single retry on
an expired access token.
"""
import requests

from . import auth as auth_mod


class RanaClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def request(self, method: str, path: str, tenant_id: str = None, query: dict = None,
                json_body=None, data=None, extra_headers: dict = None,
                retry_on_401: bool = True, timeout: float = 60) -> requests.Response:
        """
        `path` may contain `{tenant_id}`, filled in from cfg (or the tenant_id
        arg) automatically. Any other `{placeholder}` (e.g. `{project_id}`)
        must already be substituted by the caller.
        """
        tenant_id = tenant_id or self.cfg["default_tenant_id"]
        path = path.replace("{tenant_id}", tenant_id)

        token = auth_mod.get_valid_access_token(self.cfg)
        headers = {"Authorization": f"Bearer {token}"}
        if extra_headers:
            headers.update(extra_headers)

        url = self.cfg["api_base_url"].rstrip("/") + "/" + path.lstrip("/")
        resp = requests.request(
            method.upper(), url, params=query, json=json_body, data=data,
            headers=headers, timeout=timeout,
        )

        if resp.status_code == 401 and retry_on_401:
            auth_mod.get_valid_access_token(self.cfg, force_refresh=True)
            return self.request(method, path, tenant_id, query, json_body, data,
                                 extra_headers, retry_on_401=False, timeout=timeout)
        return resp

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)


class ApiError(SystemExit):
    def __init__(self, resp: requests.Response):
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        super().__init__(f"HTTP {resp.status_code} on {resp.request.method} {resp.request.url}\n{_fmt(body)}")


def _fmt(body):
    import json
    if isinstance(body, (dict, list)):
        return json.dumps(body, indent=2)
    return str(body)


def raise_for_status(resp: requests.Response):
    if not resp.ok:
        raise ApiError(resp)
    return resp
