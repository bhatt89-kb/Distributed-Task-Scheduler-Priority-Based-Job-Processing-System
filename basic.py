import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

r.set("name", "hello")

value = r.get("name")

print(value)