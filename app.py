from kitchencontrols import KitchenControlsApp
from memory import Memory
from sdsystem import SDSystem

system = SDSystem(timeout=600)
system.register_app(
    Memory(
        "./memory/memory_pics/*.jpeg",
        "./memory/memory_backside.jpeg",
        "./memory/memory_backside.jpeg",
    ),
)
system.register_app(
    KitchenControlsApp(),
)
system.start()
