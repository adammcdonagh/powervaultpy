import os


def get_test_context():
    api_key = os.environ["API_KEY"]
    if api_key is None:
        raise Exception("API_KEY must be set")

    return {
        "api_key": api_key,
    }
