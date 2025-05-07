from django.core.exceptions import ObjectDoesNotExist


class HandleObjectDoesNotExistMiddleware:
    def __init__(self, get_response):
        self.res = get_response

    def __call__(self, request):
        try:
            return self.res(request)
        except ObjectDoesNotExist as e:
            # Return a JSON response for ObjectDoesNotExist
            return 404, {"error": "The requested object does not exist.", "details": str(e)}
