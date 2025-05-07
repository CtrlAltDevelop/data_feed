from django.db import IntegrityError


class HandleObjectExistMiddleware:
    def __init__(self, get_response):
        self.res = get_response

    def __call__(self, request):
        try:
            return self.res(request)
        except IntegrityError as e:
            # Return a JSON response for ObjectDoesNotExist
            return 404, {"error": "Integrity error occurred.", "details": str(e)}
