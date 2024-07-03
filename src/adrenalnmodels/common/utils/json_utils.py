from sqlalchemy import inspect


def serialize(self):
    return {c: getattr(self, c) for c in inspect(self).attrs.keys()}


def serialize_list(obj_list):
    return [serialize(m) for m in obj_list]


def query_list_to_dict(query_list):
    return [entry._asdict() for entry in query_list]