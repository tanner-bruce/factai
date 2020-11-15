
local m = require("./msgpack")
local util = require("./util")


function find_nearby_entities(e)
      local radius = 110
      local pos = e.position;
      local px = pos.x
      local py = pos.y -- I'm just unrolling everything now...
      local area = {
         {px-radius, py-radius},
         {px+radius, py+radius}}
      return e.surface.find_entities_filtered{area = area, force = {"enemy"}}
      -- return e.surface.find_entities(area)
end

function commands.on_tick(event)
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
    -- fmt = "{tick=%d,position={x=%f,y=%f},walking_state={%s}"
    -- args = {parameter.tick, pos.x, pos.y, stringify(ws)} 
    -- str = string.format(fmt, parameter.tick, pos.x, pos.y, util.stringify(ws))


    -- ents = "["
    -- for i, ent in ipairs(find_nearby_entities(p)) do
    --     ents = ents .. string.format("{name=%s,position={%f,%f}},", ent.name, ent.position.x, ent.position.y)
    -- end
    -- ents = ents:sub(1, -2) .. "]"

    -- str = str .. ",entities=" .. ents

    -- if ic then
    --     str = str .. string.format(",shooting_state={state=%s,position={x=%f,y=%f}}", ss.state, ss.position.x, ss.position.y)
    -- end
    -- str = str .. "}"
    rcon.print(m.pack(p.walking_state))
end

function commands.enqueue(parameter)
    rcon.print("howdy")
end