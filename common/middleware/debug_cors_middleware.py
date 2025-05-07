class DebugCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("Request Origin:", request.META.get('HTTP_ORIGIN'))
        response = self.get_response(request)
        print("Response Headers:", response.headers)
        return response