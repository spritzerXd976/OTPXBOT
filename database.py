import motor.motor_asyncio
from config import MONGO_URI, MONGO_DB

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]

users_col = db["users"]
orders_col = db["orders"]
settings_col = db["settings"]
topups_col = db["topups"]
redeem_codes_col = db["redeem_codes"]


async def ensure_indexes():
    await users_col.create_index("user_id", unique=True)
    await orders_col.create_index("order_id", unique=True)
    await orders_col.create_index("sasta_id")
    await orders_col.create_index("user_id")
    await settings_col.create_index("key", unique=True)
    await topups_col.create_index("topup_id", unique=True)
    await topups_col.create_index("user_id")
    await redeem_codes_col.create_index("code", unique=True)


async def get_user(user_id: int):
    return await users_col.find_one({"user_id": user_id})


async def create_user(user_id: int, username: str, is_admin: bool, ref_by=None):
    await users_col.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "username": username or "",
                "is_admin": is_admin,
            },
            "$setOnInsert": {
                "balance": 0.0,
                "ref_by": ref_by,
                "created_at": __import__("datetime").datetime.utcnow(),
            },
        },
        upsert=True,
    )
    return await get_user(user_id)


async def update_balance(user_id: int, delta: float):
    await users_col.update_one(
        {"user_id": user_id}, {"$inc": {"balance": round(delta, 2)}}
    )


async def set_balance(user_id: int, balance: float):
    await users_col.update_one(
        {"user_id": user_id}, {"$set": {"balance": round(balance, 2)}}
    )


async def get_setting(key: str, default):
    doc = await settings_col.find_one({"key": key})
    return doc["value"] if doc else default


async def set_setting(key: str, value):
    await settings_col.update_one(
        {"key": key}, {"$set": {"value": value}}, upsert=True
    )


async def create_order(order: dict):
    await orders_col.insert_one(order)


async def update_order(order_id: str, fields: dict):
    await orders_col.update_one({"order_id": order_id}, {"$set": fields})


async def get_order(order_id: str):
    return await orders_col.find_one({"order_id": order_id})


async def get_user_orders(user_id: int, limit: int = 10):
    cursor = orders_col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_recent_orders(limit: int = 20):
    cursor = orders_col.find().sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_all_users():
    cursor = users_col.find({})
    return await cursor.to_list(length=10000)


async def count_users():
    return await users_col.count_documents({})


async def count_orders_by_status(status: str):
    return await orders_col.count_documents({"status": status})


# ---- topups ----


async def create_topup(t: dict):
    await topups_col.insert_one(t)


async def get_topup(topup_id: str):
    return await topups_col.find_one({"topup_id": topup_id})


async def update_topup(topup_id: str, fields: dict):
    await topups_col.update_one({"topup_id": topup_id}, {"$set": fields})


async def get_pending_topups(user_id: int):
    cursor = topups_col.find({"user_id": user_id, "status": "pending"}).sort("created_at", -1)
    return await cursor.to_list(length=20)


async def get_topup_by_ref(ref: str):
    return await topups_col.find_one({"utr_or_txn": ref, "status": "pending"})


# ---- redeem codes ----


async def get_redeem_code(code: str):
    return await redeem_codes_col.find_one({"code": code.upper()})


async def use_redeem_code(code: str, user_id: int):
    await redeem_codes_col.update_one(
        {"code": code.upper()},
        {"$set": {"used_by": user_id, "used_at": __import__("datetime").datetime.utcnow()}},
    )
