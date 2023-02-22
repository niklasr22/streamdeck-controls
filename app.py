from kitchencontrols import KitchenControlsApp
from memory import Memory
from sdsystem import Orientation, SDSystem


system = SDSystem(orientation=Orientation.FLIPPED_180)
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
