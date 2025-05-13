from pydantic import BaseModel


class VendorData(BaseModel):
    title: str
    description: str
    price: str
    image_link: str
    article_link: str
