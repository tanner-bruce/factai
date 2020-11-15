local factai = require "./factai/factai"

commands.add_command("enqueue", "enqueue", factai.enqueue)
commands.add_command("observe", "observe", factai.state)
script.on_event(defines.events.on_tick, factai.on_tick)