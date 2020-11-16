require "commands"

function on_init()
    global["entcache"] = {}
    global["entcache"]["coal"] = {}
    global["entcache"]["copper-ore"] = {}
    global["entcache"]["crude-oil"] = {}
    global["entcache"]["enemy-base"] = {}
    global["entcache"]["iron-ore"] = {}
    global["entcache"]["stone"] = {}
    global["entcache"]["trees"] = {}
    global["entcache"]["uranium-ore"] = {}
    global["entcache"]["dead-dry-hairy-tree"] = {}
    global["entcache"]["dead-grey-trunk"] = {}
    global["entcache"]["dead-tree-desert"] = {}
    global["entcache"]["dry-hairy-tree"] = {}
    global["entcache"]["dry-tree"] = {}
    global["entcache"]["tree-01"] = {}
    global["entcache"]["tree-02"] = {}
    global["entcache"]["tree-02-red"] = {}
    global["entcache"]["tree-03"] = {}
    global["entcache"]["tree-04"] = {}
    global["entcache"]["tree-05"] = {}
    global["entcache"]["tree-06"] = {}
    global["entcache"]["tree-06-brown"] = {}
    global["entcache"]["tree-07"] = {}
    global["entcache"]["tree-08"] = {}
    global["entcache"]["tree-08-brown"] = {}
    global["entcache"]["tree-08-red"] = {}
    global["entcache"]["tree-09"] = {}
    global["entcache"]["tree-09-brown"] = {}
    global["entcache"]["tree-09-red"] = {}
end

script.on_init(on_init)
commands.add_command("enqueue", "enqueue", commands.enqueue)
commands.add_command("observe", "observe", commands.observe)
commands.add_command("zoom", "zoom", commands.zoom)
-- script.on_event(defines.events.on_tick, commands.on_tick)