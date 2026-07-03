import httpx
from config import SASTA_API_KEY, SASTA_BASE_URL


def _params(extra: dict) -> dict:
    p = {"api_key": SASTA_API_KEY, "format": "json"}
    p.update(extra)
    return p


async def get_balance() -> float:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{SASTA_BASE_URL}/getBalance", params=_params({}))
        data = r.json()
        return float(data.get("balance", 0.0))


async def get_services_list() -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{SASTA_BASE_URL}/getServicesList", params=_params({}))
        return r.json()


async def get_services(service: str = "") -> dict:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            f"{SASTA_BASE_URL}/getServices",
            params=_params({"service": service} if service else {}),
        )
        return r.json()


async def get_number(service: str, country: str = "", max_price: str = "") -> dict:
    extra = {"service": service}
    if country:
        extra["country"] = country
    if max_price:
        extra["maxPrice"] = max_price
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{SASTA_BASE_URL}/getNumberV2", params=_params(extra))
        return r.json()


async def get_status(activation_id: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            f"{SASTA_BASE_URL}/getStatus",
            params=_params({"id": activation_id}),
        )
        return r.json()


async def set_status(activation_id: str, status: int) -> dict:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            f"{SASTA_BASE_URL}/setStatus",
            params=_params({"id": activation_id, "status": status}),
        )
        return r.json()


async def get_orders(limit: int = 20, page: int = 1, status: str = "") -> dict:
    extra = {"limit": limit, "page": page}
    if status:
        extra["status"] = status
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{SASTA_BASE_URL}/getOrders", params=_params(extra))
        return r.json()
