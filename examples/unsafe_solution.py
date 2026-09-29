"""Unsafe sample. harmness should report every built-in harm."""

import shutil
import requests


class App:
    def delete(self, _path):
        def decorate(func):
            return func

        return decorate


app = App()

api_key = "AKIA1234567890ABCDEF"
password = "s3cr3t-value"


@app.delete("/items/<item_id>")
def delete_item(item_id):
    shutil.rmtree("/data/items")
    logger.info("removed ada@company.test")


debug = True


def fetch_items():
    requests.get("https://api.company.test/items")
