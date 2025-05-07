from ninja import Schema


class HealthRes(Schema):
    status: str
    code: int
    version: str
