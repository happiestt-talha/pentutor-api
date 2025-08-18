import hashlib

def generate_secure_hash(data: dict, integrity_salt: str) -> str:
    sorted_keys = sorted(data.keys())
    string_to_hash = integrity_salt + '&' + '&'.join([str(data[k]) for k in sorted_keys])
    return hashlib.sha256(string_to_hash.encode('utf-8')).hexdigest()