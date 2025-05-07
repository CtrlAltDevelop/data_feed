from typing import Optional, Union, List
from ninja import Schema


class BaseResponse(Schema):
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseResponse):
    success: bool = False
    message: str


class ErrorContextSchema(Schema):
    error: str


class ErrorDetailSchema(Schema):
    type: str
    loc: List[Union[str, int]]
    msg: str
    ctx: Optional[ErrorContextSchema]


class ValidationErrorSchema(Schema):
    detail: List[ErrorDetailSchema]
