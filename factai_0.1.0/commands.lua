
local m = require("./msgpack")
local util = require("./util")

function find_nearby_entities(e, force)
    local radius = 110
    local pos = e.position;
    local px = pos.x
    local py = pos.y -- I'm just unrolling everything now...
    local area = {
       {px-radius, py-radius},
       {px+radius, py+radius}}
    return e.surface.find_entities_filtered{area = area, force = {force}}
    -- return e.surface.find_entities(area)
end

function get_visible_bounds(e)
    local pos = e.position;
    local px = pos.x
    local py = pos.y
    local max_w = 1920.0
    local max_h = 1080.0
    local dsc = 0.6
    local dsr = e.display_resolution
    local w_off = ((60.0*dsr.width) / (2.0*dsc*max_w))
    local h_off = ((32.0*dsr.height) / (2.0*dsc*max_h))
    return {
       {px-w_off, py-h_off},
       {px+w_off, py+h_off}}
end

function find_visible_entities(e, force)
    local area = get_visible_bounds(e)
    return e.surface.find_entities_filtered{area = area, force = {force}}
end

function commands.on_tick(event)
    local p = game.players[2]
    if not p then end
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
    -- local ent = p.character
    -- local health = ent.get_health_ratio()
    -- local kills = ent.kills
    -- local sel = p.selected
    -- local effects = ent.effects
    -- local cmp = p.character_mining_progress
    -- local cq = p.crafting_queue

    -- local last_dmg = ent.tick_of_last_damage
    -- local aqbs = p.get_active_quick_bar_page
end

function commands.observe(parameter)
    local p = game.players[1]
    if not p then end
    local pos = p.position
    local ws = p.walking_state
    local rds = p.riding_state
    local ms = p.mining_state
    local ss = p.shooting_state
    local ps = p.picking_state
    local rs = p.repair_state
    local cs = p.cursor_stack
    local cg = p.cursor_ghost

    -- local cq = p.crafting_queue
    local ic = p.in_combat
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

    local player_feature_vec = {
        parameter.tick,pos,ws,ic,ss
    }
    entities = {}
    for i, ent in ipairs(find_visible_entities(p)) do
        el = entities[ent.name] or {}
        table.insert(el, {ent.position, ent.health, ent.get_health_ratio()})
        entities[ent.name] = el
    end

    out = {
        player_feature_vec,
        entities
    }

    rcon.print(m.pack(out))
end

function commands.enqueue(parameter)
    rcon.print("howdy")
end

function commands.zoom(parameter)
    local p = game.players[1]
    if not p then return end
    p.zoom = parameter.parameter
    rcon.print(m.pack{p.display_resolution,parameter})
end