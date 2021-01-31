import time
import jwt
from uuid import UUID


def generate_jwt(key, secret):
    header = {"alg": "HS256", "typ": "JWT"}

    payload = {"iss": key, "exp": int(time.time() + 3600)}

    token = jwt.encode(payload, secret, algorithm="HS256", headers=header)
    return token.decode("utf-8")


def is_valid_uuid(uuid_to_test, version=4):

    try:
        uuid_object = UUID(hex=uuid_to_test, version=version)
    except ValueError:
        return False

    return str(uuid_object) == uuid_to_test
