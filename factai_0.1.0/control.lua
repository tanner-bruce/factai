require "commands"

commands.add_command("enqueue", "enqueue", commands.enqueue)
commands.add_command("observe", "observe", commands.observe)
script.on_event(defines.events.on_tick, commands.on_tick)