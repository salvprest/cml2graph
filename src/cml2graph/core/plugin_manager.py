
import importlib
import logging
import pkgutil

from cml2graph.core.language_schema import LanguagePlugin, Renderer

logger = logging.getLogger(__name__)


class PluginManager:
    """Discovers, registers, and provides access to language plugins."""

    _DEFAULT_PLUGINS_PACKAGE = "cml2graph.plugins"

    def __init__(self) -> None:
        self._plugins: dict[str, LanguagePlugin] = {}
        self.discover(self._DEFAULT_PLUGINS_PACKAGE)

    # Registration
    def register(self, plugin: LanguagePlugin) -> None:
        if not isinstance(plugin, LanguagePlugin):
            missing = self._find_missing(plugin)
            raise TypeError(
                f"{type(plugin).__name__} does not satisfy LanguagePlugin protocol. "
                f"Missing: {missing}"
            )

        name = plugin.name
        if name in self._plugins:
            logger.warning(
                "Plugin '%s' already registered — overwriting with %s",
                name,
                type(plugin).__name__,
            )
        self._plugins[name] = plugin
        logger.info("Registered plugin: %s", name)

    # Discovery
    def discover(self, package_name: str) -> None:
        try:
            package = importlib.import_module(package_name)
        except ModuleNotFoundError as e:
            raise ImportError(
                f"Plugin package '{package_name}' not found"
            ) from e

        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            if not is_pkg:
                continue
            fqn = f"{package_name}.{module_name}"
            try:
                module = importlib.import_module(fqn)
            except Exception:
                logger.exception("Failed to import plugin module: %s", fqn)
                continue

            for attr_name in dir(module):
                if not attr_name.endswith("Plugin"):
                    continue
                attr = getattr(module, attr_name)
                if not isinstance(attr, type):
                    continue
                try:
                    self.register(attr())
                except Exception:
                    logger.exception(
                        "Failed to instantiate %s from %s", attr_name, fqn
                    )

    # Look-ups
    def get(self, name: str) -> LanguagePlugin:
        try:
            return self._plugins[name]
        except KeyError:
            available = ", ".join(sorted(self._plugins)) or "(none)"
            raise KeyError(
                f"Plugin '{name}' not found. Available: {available}"
            ) from None

    # TODO: I don't like this here
    def get_renderer(self, plugin_name: str, fmt: str | None = None) -> Renderer:
        """
        Short-cut: grab a specific renderer from a plugin.

        ``fmt=None`` returns the default renderer.
        """
        plugin = self.get(plugin_name)
        renderers = plugin.get_renderers()
        key = fmt or plugin.default_renderer_name
        try:
            return renderers[key]
        except KeyError:
            available = ", ".join(sorted(renderers)) or "(none)"
            raise KeyError(
                f"Renderer '{key}' not found in plugin '{plugin_name}'. "
                f"Available: {available}"
            ) from None

    @property
    def available(self) -> list[str]:
        return sorted(self._plugins)

    # Helpers
    @staticmethod
    def _find_missing(obj: object) -> list[str]:
        required_props = {"name", "default_renderer_name"}
        required_methods = {"parse", "get_filters", "get_renderers", "render"}
        missing: list[str] = []
        for attr in required_props | required_methods:
            if not hasattr(obj, attr):
                missing.append(attr)
            elif attr in required_methods and not callable(getattr(obj, attr)):
                missing.append(f"{attr} (not callable)")
        return missing