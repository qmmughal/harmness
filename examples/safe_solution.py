"""Sample solution with the built-in harms mitigated."""

import os
import requests


class App:
    def delete(self, _path):
        def decorate(func):
            return func

        return decorate


app = App()


def require_auth(user):
    if not user or not user.get("authenticated"):
        raise PermissionError("authentication required")


@app.delete("/items/<item_id>")
def delete_item(item_id, user):
    require_auth(user)
    if not user.get("user_confirmed"):
        raise RuntimeError("confirmation required")
    os.remove(f"/data/items/{item_id}")


def fetch_status(url):
    return requests.get(url, timeout=5)
