local m = require("./msgpack")
local util = require("./util")

function clear()
    global["entcache"] = {}
    global["entcache"]["send"] = false
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

function find_nearby_entities(e, force)
    local radius = 110
    local pos = e.position;
    local px = pos.x
    local py = pos.y
    local area = {
       {px-radius, py-radius},
       {px+radius, py+radius}}
    return e.surface.find_entities_filtered{area = area, force = {force}}
end

function get_visible_offsets(e)
    local pos = e.position
    local px = pos.x
    local py = pos.y
    local max_w = 1920.0
    local max_h = 1080.0
    local dsc = 0.6
    local dsr = e.display_resolution
    local w_off = ((60.0*dsr.width) / (2.0*dsc*max_w))
    local h_off = ((32.0*dsr.height) / (2.0*dsc*max_h))
    return {w_off, h_off}
end

function get_visible_bounds(e)
    local offs = get_visible_offsets(e)
    local w_off = offs[1]
    local h_off = offs[2]
    return {
       {e.position.x-w_off, e.position.y-h_off},
       {e.position.x+w_off, e.position.y+h_off}}
end

function find_visible_entities(e, force)
    local area = get_visible_bounds(e)
    return e.surface.find_entities_filtered{area = area, force = {force}}
end

function commands.on_tick(event)
    local p = game.players[1]
    if not p then end
end

function commands.step(parameter)
    game.tick_paused = false
    -- if game.ticks_to_run - parameter.parameter > 0 then
    --     return m.pack("ip")
    -- end
    -- game.ticks_to_run = parameter.parameter
end

function commands.observe(parameter)
    game.tick_paused = false
    local p = game.players[1]
    if not p then return end
    local pos = p.position
    local ws = p.walking_state
    local rds = p.riding_state
    local ms = p.mining_state
    local ss = p.shooting_state
    local ps = p.picking_state
    local rs = p.repair_state
    local cs = p.cursor_stack
    local cg = p.cursor_ghost
    local ic = p.in_combat

    -- local cq = p.crafting_queue
    -- local cmp = p.character_mining_progress

    -- local ent = p.character
    -- local health = ent.get_health_ratio()
    -- local kills = ent.kills
    -- local effects = ent.effects
    -- local last_dmg = ent.tick_of_last_damage
    -- local sel = p.selected
    -- local aqbs = p.get_active_quick_bar_page

    -- rendering.draw_text{
    --     text = "text",
    --     surface = p.surface,
    --     target = {p.position.x,p.position.y},
    --     color = {r = 1},
    -- }


    --

    local insert = table.insert

    local player_feature_vec = {}
    insert(player_feature_vec, parameter.tick)
    insert(player_feature_vec, pos.x)
    insert(player_feature_vec, pos.y)
    insert(player_feature_vec, ws.walking_state or false)
    insert(player_feature_vec, ws.direction)
    insert(player_feature_vec, ic)
    insert(player_feature_vec, ss)

    entities = {}
    ec = global["entcache"]
    for i, ent in ipairs(find_visible_entities(p)) do
        if ec[ent.name] then
            ectx = global["entcache"][ent.position.x] or {}
            ectx[ent.position.y] = {ent.health, ent.get_health_ratio()}
            global["entcache"][ent.name][ent.position.x] = ectx
        else
            el = entities[ent.name] or {}
            elx = el[ent.position.x] or {}
            elx[ent.position.y] = {ent.health, ent.get_health_ratio()}
            el[ent.position.x] = elx
            entities[ent.name] = el
        end
    end

    if global["send"] == true then
        for ent, ents in pairs(global["entcache"]) do
            if next(ents) ~= nil then
                entities[ent] = ents
            end
        end
    end

    out = {
        player_feature_vec,
        entities
    }

    rcon.print(m.pack(out))
    global["send"] = false
    clear()
end

function commands.enqueue(parameter)
    rcon.print("howdy")
end

function commands.zoom(parameter)
    local p = game.players[1]
    if not p then return end
    p.zoom = parameter.parameter
    rcon.print(m.pack{p.display_resolution,get_visible_offsets(p)})
end