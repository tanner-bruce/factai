require("./msgpack")

local function val_to_str ( v )
  if "string" == type( v ) then
    v = string.gsub( v, "\n", "\\n" )
    if string.match( string.gsub(v,"[^'\"]",""), '^"+$' ) then
      return "'" .. v .. "'"
    end
    return '"' .. string.gsub(v,'"', '\\"' ) .. '"'
  else
    return "table" == type( v ) and table.stringify( v ) or 
    tostring( v )
  end
end

local function key_to_str ( k )
  if "string" == type( k ) and string.match( k, "^[_%a][_%a%d]*$" ) then
    return k
  else
    return "[" .. val_to_str( k ) .. "]"
  end
end


function stringify(tbl)
  local result, done = {}, {}
  for k, v in ipairs( tbl ) do
    table.insert( result, val_to_str( v ) )
    done[ k ] = true
  end
  for k, v in pairs( tbl ) do
    if not done[ k ] then
      table.insert( result,
        key_to_str( k ) .. "=" .. val_to_str( v ) )
    end
  end
  return "{" .. table.concat( result, "," ) .. "}"
end

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


function Ticker(event)
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

    if not global["walk_ticks"] then global["walk_ticks"] = 0 end

    if global["walk_ticks"] > 0 then
        game.players[1].walking_state = {walking = true, direction=defines.direction.east}
        global["walk_ticks"] = global["walk_ticks"] - 1
    end

    -- rendering.draw_text{
    --     text = "text",
    --     surface = p.surface,
    --     target = {p.position.x,p.position.y},
    --     color = {r = 1},
    -- }
end

function state(parameter)
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
    fmt = "{tick=%d,position={x=%f,y=%f},walking_state={%s}"
    -- args = {parameter.tick, pos.x, pos.y, stringify(ws)} 
    str = string.format(fmt, parameter.tick, pos.x, pos.y, stringify(ws))

    ents = "["
    for i, ent in ipairs(find_nearby_entities(p)) do
        ents = ents .. string.format("{name=%s,position={%f,%f}},", ent.name, ent.position.x, ent.position.y)
    end
    ents = ents:sub(1, -2) .. "]"

    str = str .. ",entities=" .. ents

    if ic then
        str = str .. string.format(",shooting_state={state=%s,position={x=%f,y=%f}}", ss.state, ss.position.x, ss.position.y)
    end
    str = str .. "}"
    rcon.print(str)
end

function cmd(parameter)
    global["walk_ticks"] = 120
    rcon.print("howdy")
end

commands.add_command("cmd", "stream", cmd)
commands.add_command("state", "state", state)
script.on_event(defines.events.on_tick, Ticker)