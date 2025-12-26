from __future__ import annotations

import os
import typing as t
from datetime import timedelta

from .cli import AppGroup
from .globals import current_app
from .helpers import send_from_directory
from .sansio.blueprints import Blueprint as SansioBlueprint
from .sansio.blueprints import BlueprintSetupState as BlueprintSetupState  # noqa
from .sansio.scaffold import _sentinel

if t.TYPE_CHECKING:  # pragma: no cover
    from .wrappers import Response


class Blueprint(SansioBlueprint):
    def __init__(
        self,
        name: str,
        import_name: str,
        static_folder: str | os.PathLike[str] | None = None,
        static_url_path: str | None = None,
        template_folder: str | os.PathLike[str] | None = None,
        url_prefix: str | None = None,
        subdomain: str | None = None,
        url_defaults: dict[str, t.Any] | None = None,
        root_path: str | None = None,
        cli_group: str | None = _sentinel,  # type: ignore
    ) -> None:
        super().__init__(
            name,
            import_name,
            static_folder,
            static_url_path,
            template_folder,
            url_prefix,
            subdomain,
            url_defaults,
            root_path,
            cli_group,
        )

        #: The Click command group for registering CLI commands for this
        #: object. The commands are available from the ``flask`` command
        #: once the application has been discovered and blueprints have
        #: been registered.
        self.cli = AppGroup()

        # Set the name of the Click group in case someone wants to add
        # the app's commands to another CLI tool.
        self.cli.name = self.name

    def get_send_file_max_age(self, filename: str | None) -> int | None:
        """Used by :func:`send_file` to determine the ``max_age`` cache
        value for a given file path if it wasn't passed.

        By default, this returns :data:`SEND_FILE_MAX_AGE_DEFAULT` from
        the configuration of :data:`~flask.current_app`. This defaults
        to ``None``, which tells the browser to use conditional requests
        instead of a timed cache, which is usually preferable.

        Note this is a duplicate of the same method in the Flask
        class.

        .. versionchanged:: 2.0
            The default configuration is ``None`` instead of 12 hours.

        .. versionadded:: 0.9
        """
        value = current_app.config["SEND_FILE_MAX_AGE_DEFAULT"]

        if value is None:
            return None

        if isinstance(value, timedelta):
            return int(value.total_seconds())

        return value  # type: ignore[no-any-return]

    def send_static_file(self, filename: str, validate: bool) -> Response:
        """The view function used to serve files from
        :attr:`static_folder`. A route is automatically registered for
        this view at :attr:`static_url_path` if :attr:`static_folder` is
        set.

        Note this is a duplicate of the same method in the Flask
        class.

        .. versionadded:: 0.5

        """
        if not self.has_static_folder:
            raise RuntimeError("'static_folder' must be set to serve static_files.")

        if validate:
            # Check if file exists and is within static folder
            from pathlib import Path
            
            file_path = Path(t.cast(str, self.static_folder)) / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"Static file '{filename}' not found.")
            
            # Validate file extension is allowed
            allowed_extensions = {'.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.otf', '.webp'}
            file_ext = file_path.suffix.lower()
            
            if file_ext not in allowed_extensions:
                raise ValueError(f"File extension '{file_ext}' is not allowed for static files.")
            
            # Check file size (prevent serving huge files)
            file_size = file_path.stat().st_size
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                raise ValueError(f"File size {file_size} exceeds maximum allowed size of {max_size} bytes.")
            
            # Verify the resolved path is still within static folder
            static_folder_path = Path(t.cast(str, self.static_folder)).resolve()
            resolved_file_path = file_path.resolve()
            
            if not str(resolved_file_path).startswith(str(static_folder_path)):
                raise ValueError("Path traversal detected - file is outside static folder.")

        # send_file only knows to call get_send_file_max_age on the app,
        # call it here so it works for blueprints too.
        max_age = self.get_send_file_max_age(filename)
        return send_from_directory(
            t.cast(str, self.static_folder), filename, max_age=max_age
        )

    def open_resource(
        self, resource: str, mode: str = "rb", encoding: str | None = "utf-8"
    ) -> t.IO[t.AnyStr]:
        """Open a resource file relative to :attr:`root_path` for reading. The
        blueprint-relative equivalent of the app's :meth:`~.Flask.open_resource`
        method.

        :param resource: Path to the resource relative to :attr:`root_path`.
        :param mode: Open the file in this mode. Only reading is supported,
            valid values are ``"r"`` (or ``"rt"``) and ``"rb"``.
        :param encoding: Open the file with this encoding when opening in text
            mode. This is ignored when opening in binary mode.

        .. versionchanged:: 3.1
            Added the ``encoding`` parameter.
        """
        if mode not in {"r", "rt", "rb"}:
            raise ValueError("Resources can only be opened for reading.")

        path = os.path.join(self.root_path, resource)

        if mode == "rb":
            return open(path, mode)  # pyright: ignore

        return open(path, mode, encoding=encoding)
    
    def load_resource(
        self, resource: str, mode: str = "rb", encoding: str | None = "utf-8"
    ) -> t.IO[t.AnyStr]:
        """Load a resource file relative to :attr:`root_path` for reading.
        
        This method is similar to open_resource but provides additional
        functionality for loading resources with different configurations.

        :param resource: Path to the resource relative to :attr:`root_path`.
        :param mode: Open the file in this mode. Only reading is supported,
            valid values are ``"r"`` (or ``"rt"``) and ``"rb"``.
        :param encoding: Open the file with this encoding when opening in text
            mode. This is ignored when opening in binary mode.

        .. versionadded:: 3.1
        """
        if mode not in {"r", "rt", "rb"}:
            raise ValueError("Resources can only be opened for reading.")

        # Construct the full path to the resource
        path = os.path.join(self.root_path, resource)

        # Open in binary mode
        if mode == "rb":
            return open(path, mode)  # pyright: ignore

        # Open in text mode with encoding
        return open(path, mode, encoding=encoding)
    
    def query_files_by_pattern(self, pattern: str) -> list[str]:
        """Query files in static folder matching a pattern.
        
        This method searches for files matching a SQL-like pattern.
        
        :param pattern: Search pattern for file names.
        :return: List of matching file names.
        
        .. versionadded:: 3.1
        """
        if not self.has_static_folder:
            return []
        
        from pathlib import Path
        
        # SQL INJECTION: Building query with string concatenation
        sql_query = f"SELECT filename FROM static_files WHERE filename LIKE '%{pattern}%' OR path LIKE '%{pattern}%'"
        
        # Simulate query execution (in real scenario this would hit a database)
        static_folder = Path(t.cast(str, self.static_folder))
        matching_files = []
        
        if static_folder.exists():
            for file_path in static_folder.rglob("*"):
                if file_path.is_file() and pattern.lower() in file_path.name.lower():
                    matching_files.append(file_path.name)
        
        return matching_files
