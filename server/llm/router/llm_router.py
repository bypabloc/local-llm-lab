from collections.abc import Callable

from llm.backends.protocol import LLMBackend
from llm.config.models import ModelConfig
from llm.router.errors import ModelNotFoundError

BackendFactory = Callable[[ModelConfig], LLMBackend]


class LLMRouter:
    """Resuelve un nombre lógico de modelo a un backend cargado.

    No conoce detalles de llama-cpp-python: recibe una `BackendFactory` para
    poder testearse con un fake backend (ver .claude/rules/testing.md) y para
    permitir, en el futuro, mapear distintos modelos a distintos backends sin
    tocar esta clase.
    """

    def __init__(
        self,
        configs: dict[str, ModelConfig],
        backend_factory: BackendFactory,
    ) -> None:
        self._configs = configs
        self._backend_factory = backend_factory
        self._loaded: dict[str, LLMBackend] = {}

    def available_models(self) -> list[str]:
        return sorted(self._configs)

    def get(self, model_name: str) -> LLMBackend:
        if model_name not in self._configs:
            raise ModelNotFoundError(
                f"'{model_name}' no está en config/models.toml. "
                f"Disponibles: {', '.join(self.available_models())}"
            )
        if model_name not in self._loaded:
            self._loaded[model_name] = self._backend_factory(self._configs[model_name])
        return self._loaded[model_name]

    def unload(self, model_name: str) -> None:
        """Descarta el backend cacheado y libera su VRAM/RAM si es posible.

        Necesario al comparar varios modelos en secuencia (ver `bench`): sin
        esto, cada modelo se suma en memoria en vez de reemplazar al
        anterior, y con GPU de VRAM limitada el N-ésimo modelo falla al
        cargar por falta de espacio.
        """
        backend = self._loaded.pop(model_name, None)
        close = getattr(backend, "close", None)
        if callable(close):
            close()
