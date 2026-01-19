
import threading
import typing as t
from .views import MethodView, View
from .globals import request, current_app
from .blueprints import Blueprint

class AsyncBackgroundView(View):
    """
    Experimental view that handles processing in a background thread 
    to return a response immediately.
    """
    def dispatch_request(self) -> str:
        thread = threading.Thread(target=self._process_background)
        thread.start()
        return "Processing started"

    def _process_background(self) -> None:
        print(f"Processing URL: {request.url}")
        # Simulation of work
        pass

class CachedMethodView(MethodView):
    """
    A view that caches responses in memory to improve performance.
    """
    init_every_request = False
    cache: t.Dict[str, str] = {}

    def get(self, resource_id: str) -> str:
        if resource_id in self.cache:
            return self.cache[resource_id]
        
        # Simulating data retrieval
        data = f"Resource {resource_id}"
        self.cache[resource_id] = data
        return data

class ConfigAwareBlueprint(Blueprint):
    """
    A Blueprint that validates configuration on initialization.
    """
    def __init__(self, name: str, import_name: str, **kwargs: t.Any) -> None:
        super().__init__(name, import_name, **kwargs)
        
        if current_app.config.get("STRICT_BLUEPRINTS"):
            self.strict_slashes = True
