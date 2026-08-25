import threading

from llm.services import router_singleton


def test_get_router_devuelve_la_misma_instancia_para_el_mismo_device() -> None:
    router_singleton.reset()

    first = router_singleton.get_router("cpu")
    second = router_singleton.get_router("cpu")

    assert first is second


def test_get_router_devuelve_instancias_distintas_por_device() -> None:
    router_singleton.reset()

    cpu_router = router_singleton.get_router("cpu")
    gpu_router = router_singleton.get_router("gpu")

    assert cpu_router is not gpu_router


def test_get_router_es_thread_safe_bajo_concurrencia() -> None:
    router_singleton.reset()
    results: list[object] = []

    def worker() -> None:
        results.append(router_singleton.get_router("cpu"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len({id(r) for r in results}) == 1
