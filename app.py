from kitchencontrols import KitchenControlsApp
from memory import Memory
from rgb_recovery import RgbRecovery
from sdsystem import SDSystem

system = SDSystem(timeout=600)
system.register_app(Memory())
system.register_app(KitchenControlsApp())
system.register_app(RgbRecovery())
system.start()
