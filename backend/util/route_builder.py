"""Fluent-style helper for defining Flask routes on a Blueprint.

Auth wrapper code is currently commented out; related imports removed to avoid
lint warnings. Reintroduce them when enabling auth.
"""
# from functools import wraps  # (re-enable when auth decorator is restored)
# from flask import session, jsonify  # (used only by commented auth code)


class RouteBuilder:
    """Route builder with a chainable API."""
    def __init__(self, blueprint):
        """
        Initialize the builder with a Flask Blueprint.

        Parameters
        ----------
        blueprint : flask.Blueprint
            The Flask Blueprint where the route will be registered.
        """
        self.bp = blueprint
        self._rule = None
        self._endpoint = None
        self._methods = []
        self._auth = False
        self._handler = None

    def route(self, rule, endpoint=None):
        """
        Set the route path and optional endpoint name.

        Parameters
        ----------
        rule : str
            The URL rule (e.g., "/health").
        endpoint : str, optional
            Custom endpoint name. Default to the handler function name.
        """
        self._rule = rule
        self._endpoint = endpoint
        return self

    def methods(self, *methods):
        """
        Define allowed HTTP methods for the route.

        Parameters
        ----------
        *methods : str
            One or more HTTP methods (e.g., "GET", "POST").
        """
        self._methods = methods
        return self

    def auth_required(self):
        """
        Mark the route as requiring authentication.

        Notes
        -----
        Currently relies on `_wrap_auth`, which is a placeholder for
        Google or Supabase session validation.
        """
        self._auth = True
        return self

    def handler(self, func):
        """
        Set the handler function for the route.

        If `auth_required()` was called, the handler will be wrapped
        with an authentication check before registration.

        Parameters
        ----------
        func : callable
            The route handler function.
        """
        if self._auth:
            func = self._wrap_auth(func)
        self._handler = func
        return self

    def build(self):
        """
        Finalize and register the route with the Blueprint.

        Returns
        -------
        RouteBuilder
            Self, after the route is added.
        """
        self.bp.add_url_rule(
            self._rule,
            endpoint=self._endpoint or self._handler.__name__,
            view_func=self._handler,
            methods=self._methods
        )
        return self

    # TODO Readd auth from either Google or Supabase
    # def _wrap_auth(self, func):
    #     """
    #     Wrap a route handler with authentication logic.
    #
    #     Checks session for AWS or Google tokens before
    #     allowing the handler to execute.
    #
    #     Returns
    #     -------
    #     callable
    #         The wrapped handler with authentication checks.
    #     """
    #     @wraps(func)
    #     def decorated(*args, **kwargs):
    #         if 'aws_session_token' not in session or 'google_token' not in session:
    #             return jsonify({"error": "User not logged in"}), 401
    #         user_info = session.get("google_token", {}).get("userinfo", {})
    #         if not user_info or "email" not in user_info:
    #             return jsonify({"error": "User session invalid"}), 401
    #         return func(*args, **kwargs)
    #     return decorated
