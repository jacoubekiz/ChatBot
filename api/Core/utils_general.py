import hashlib


def hash_key(apiKey: str) -> str:
    """Generate SHA256 hash of the given API key."""
    return hashlib.sha256(apiKey.encode()).hexdigest()


def read_json(file_path, encoding='utf-8'):
    """Read and parse JSON file."""
    import json
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        return
    except json.JSONDecodeError as e:
        return
