# TODO Test if blueprint imports still work under the same process in app.py

"""
Route Template

Note:   Unlike that of MyElement and RealDoc, this project will be adapting a
        builder design pattern for the way we're doing routes. (OOP) This 
        design pattern will consist of three parts.
        
        1. builder.py:  This contains the class in which is used for building
                        each route. Each builder has the following:
                            self.bp         Flask blueprint entity.
                            self._rule      The /destination in the request.
                            self._endpoint  Endpoint/handler name.
                            self._methods   GET/POST/PUT/DELETE
                            self._auth      Flags authetnication requirement.
                            self._handler   Name of the function handler.
        2. Handlers:    Function(s) containing the logic for eaech route in 
                        handling requests and processing them. These can
                        access the request body as 'request.json'
        3. Route:       Built using the blueprint, defines the properties of
                        the route as to which handler to call, if auth is
                        needed, etc.

Steps for setting up a new route file:

    1. Copy and rename this file (e.g., my_feature_routes.py).
    2. Register the blueprint in app.py: 
        from my_feature_routes import new_bp
        app.register_blueprint(new_bp, url_prefix='/api/my-feature')
    3. Customize the endpoint logic below and remove any unused imports.
    4. Follow each #TODO and delete the comment when done.
    5. Delete this docstring header when finished.
"""

# TODO Add/remove imports as needed, highly recommended to study flask imports
from flask import Blueprint, request, jsonify, send_file
from util.route_builder import RouteBuilder

bp = Blueprint('example', __name__)

# Example ping request
def ping():
    return jsonify({"status": "ok"})

# Example builder with parameters set up for ping request
RouteBuilder(bp) \
    .route('/ping') \
    .methods('GET') \
    .handler(ping) \
    .build()
