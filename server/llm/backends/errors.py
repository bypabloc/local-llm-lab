class BackendLoadError(Exception):
    """El backend no pudo cargar el modelo (path inválido, GGUF corrupto, etc.)."""
