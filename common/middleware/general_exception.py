import logging


class HandleExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # Log the exception for debugging
            logging.error("An unexpected error occurred: %s", str(e), exc_info=True)
            # Return a generic error response
            return 500, {"error": "An unexpected error occurred.", "details": str(e)}
