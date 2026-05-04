"""Dummy Todo API server for testing OpenAPI integrations.

Run:  python scratch/todo_server.py
Serves on http://localhost:9999
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Simple Todo API", version="1.0.0")

# In-memory store with seed data
_next_id = 4
_todos = [
    {"id": 1, "task": "Buy groceries", "completed": False},
    {"id": 2, "task": "Walk the dog", "completed": True},
    {"id": 3, "task": "Read a book", "completed": False},
]

_products = [
    {"id": 1, "name": "Laptop", "price": 999.99},
    {"id": 2, "name": "Smartphone", "price": 499.99},
    {"id": 3, "name": "Universal Charger", "price": 29.99},
]

_orders = [
    {"id": 145, "product_id": 1, "quantity": 1, "total_price": 999.99},
    {"id": 146, "product_id": 2, "quantity": 2, "total_price": 999.98},
    {"id": 147, "product_id": 3, "quantity": 3, "total_price": 89.97},
]


class TodoCreate(BaseModel):
    task: str
    completed: bool = False


class TodoUpdate(BaseModel):
    task: Optional[str] = None
    completed: Optional[bool] = None


@app.get("/todos")
def list_todos():
    return _todos

@app.get("/products/{product_id}")
def get_product(product_id: int):
    for p in _products:
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Product not found")


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    for o in _orders:
        if o["id"] == order_id:
            return o
    raise HTTPException(status_code=404, detail="Order not found")

@app.post("/todos", status_code=201)
def create_todo(body: TodoCreate):
    global _next_id
    todo = {"id": _next_id, "task": body.task, "completed": body.completed}
    _next_id += 1
    _todos.append(todo)
    return todo


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    for t in _todos:
        if t["id"] == todo_id:
            return t
    raise HTTPException(status_code=404, detail="Todo not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9999)
